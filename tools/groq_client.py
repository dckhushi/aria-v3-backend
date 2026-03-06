"""
ARIA v3 — AI Client (OpenRouter)
Drop-in replacement for Groq — same API format
Free models: mistralai/mistral-7b-instruct, meta-llama/llama-3.1-8b-instruct
"""
import os
import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL   = "meta-llama/llama-3.1-8b-instruct:free"  # 100% free model

def get_key():
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")
    return key

def chat(messages: list, tools: list = None, temperature: float = 0.5, max_tokens: int = 2048) -> dict:
    key = get_key()
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://aria-v3.onrender.com",
            "X-Title": "ARIA v3"
        },
        json=payload,
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()

def simple_chat(system: str, user: str, temperature: float = 0.5) -> str:
    data = chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        temperature=temperature
    )
    return data["choices"][0]["message"]["content"]
