import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import jwt
import psycopg
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.environ["JWT_SECRET"]
security = HTTPBearer()


class UserIn(BaseModel):
    username: str
    password: str


@app.post("/register")
async def register(user: UserIn):
    # make a random salt and mix it with the password before hashing
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + user.password).encode()).hexdigest()
    saved = salt + "$" + hashed

    try:
        async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
            await conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (user.username, saved),
            )
    except psycopg.errors.UniqueViolation:
        return {"error": "username already taken"}

    return {"message": "user created"}


@app.post("/login")
async def login(user: UserIn):
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        cur = await conn.execute(
            "SELECT password_hash FROM users WHERE username = %s", (user.username,)
        )
        row = await cur.fetchone()

    if row is None:
        return {"error": "wrong username or password"}

    # the saved value looks like "salt$hash", so split it apart
    salt, saved_hash = row[0].split("$")
    hashed = hashlib.sha256((salt + user.password).encode()).hexdigest()

    if hashed != saved_hash:
        return {"error": "wrong username or password"}

    token = jwt.encode(
        {"username": user.username, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"token": token}


async def save_calculation(a, b, op, result, username):
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        await conn.execute(
            "INSERT INTO calculations (a, b, op, result, username) VALUES (%s, %s, %s, %s, %s)",
            (a, b, op, result, username),
        )


@app.get("/calculate")
async def calculate(
    a: int,
    b: int,
    op: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return {"error": "please log in first"}

    username = payload["username"]

    if op == "+":
        result = a + b
    elif op == "-":
        result = a - b
    elif op == "*":
        result = a * b
    elif op == "/":
        if b == 0:
            return {"error": "cannot divide by zero"}
        result = a / b
    else:
        return {"error": "unknown operator"}

    await save_calculation(a, b, op, result, username)
    return {"result": result}


@app.get("/history")
async def history():
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        cur = await conn.execute(
            "SELECT id, a, b, op, result, created_at, username FROM calculations ORDER BY id DESC LIMIT 50"
        )
        rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "a": r[1],
            "b": r[2],
            "op": r[3],
            "result": r[4],
            "created_at": str(r[5]),
            "username": r[6],
        }
        for r in rows
    ]
import httpx

RAZORPAY_KEY_ID = os.environ["RAZORPAY_KEY_ID"]
RAZORPAY_KEY_SECRET = os.environ["RAZORPAY_KEY_SECRET"]

class OrderIn(BaseModel):
    amount_rupees: int
    product: str

@app.post("/payments/create")
async def create_payment(order: OrderIn):
    amount_paise = order.amount_rupees * 100
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.razorpay.com/v1/orders",
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
            json={
                "amount": amount_paise,
                "currency": "INR",
                "notes": {"product": order.product},
            },
        )
    data = response.json()
    if response.status_code != 200:
        return {"error": data}
    return {"order_id": data["id"], "key_id": RAZORPAY_KEY_ID, "amount": amount_paise}

@app.get("/payments/{payment_id}/status")
async def payment_status(payment_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.razorpay.com/v1/payments/{payment_id}",
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
        )
    data = response.json()
    if response.status_code != 200:
        return {"error": data}
    return {
        "payment_id": data["id"],
        "status": data["status"],
        "amount_rupees": data["amount"] / 100,
        "order_id": data.get("order_id"),
        "method": data.get("method"),
    }