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