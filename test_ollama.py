import requests

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

if __name__ == "__main__":
    sample = "I go to store yesterday and buyed some apple."
    result = analyze_writing(sample)
    print("=== Ollama's Analysis ===")
    print(result)