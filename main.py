import os

import psycopg
from fastapi import FastAPI

app = FastAPI()


def save_calculation(a, b, op, result):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(
            "INSERT INTO calculations (a, b, op, result) VALUES (%s, %s, %s, %s)",
            (a, b, op, result),
        )

@app.get("/history")
def history():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        rows = conn.execute(
            "SELECT id, a, b, op, result, created_at FROM calculations ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return [
        {"id": r[0], "a": r[1], "b": r[2], "op": r[3], "result": r[4], "created_at": str(r[5])}
        for r in rows
    ]
    
@app.get("/calculate")
def calculate(a: int, b: int, op: str):
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

    save_calculation(a, b, op, result)
    return {"result": result}