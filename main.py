import os

import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def save_calculation(a, b, op, result):
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        await conn.execute(
            "INSERT INTO calculations (a, b, op, result) VALUES (%s, %s, %s, %s)",
            (a, b, op, result),
        )


@app.get("/calculate")
async def calculate(a: int, b: int, op: str):
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

    await save_calculation(a, b, op, result)
    return {"result": result}


@app.get("/history")
async def history():
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        cur = await conn.execute(
            "SELECT id, a, b, op, result, created_at FROM calculations ORDER BY id DESC LIMIT 50"
        )
        rows = await cur.fetchall()
    return [
        {"id": r[0], "a": r[1], "b": r[2], "op": r[3], "result": r[4], "created_at": str(r[5])}
        for r in rows
    ]