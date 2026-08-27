from fastapi import FastAPI

app = FastAPI(title="Salary Calculator Web")

@app.get("/")
def health():
    return {"status": "ok"}