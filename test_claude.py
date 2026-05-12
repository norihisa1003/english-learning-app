import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

def analyze_writing(text: str) -> str:
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"Please analyze the following English writing for grammar errors:\n\n{text}"
            }
        ]
    )
    return message.content[0].text

if __name__ == "__main__":
    sample = "I go to store yesterday and buyed some apple."
    result = analyze_writing(sample)
    print("=== Claude's Analysis ===")
    print(result)
