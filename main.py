from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

class WritingInput(BaseModel):
    text: str

def analyze_writing(text: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2",
            "prompt": f"Please analyze the following English writing for grammar errors:\n\n{text}",
            "stream": False
        }
    )
    return response.json()["response"]

@app.post("/analyze")
def analyze(input: WritingInput):
    result = analyze_writing(input.text)
    return {"result": result}