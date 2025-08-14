from src.embeddings.indexer import search
import os
import requests

BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL = os.getenv("LMSTUDIO_MODEL")

async def ask_lmstudio(question: str, context: str):
    url = f"{BASE_URL}/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "Ты — ассистент, отвечающий строго по предоставленным данным."},
            {"role": "user", "content": f"Контекст:\n{context}\n\nВопрос: {question}"}
        ],
        "temperature": 0.2
    }
    r = requests.post(url, json=payload)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

@dp.message()
async def handle_message(message: Message):
    query = message.text
    chunks = search(query, top_k=int(os.getenv("TOP_K", 4)))
    context_text = "\n---\n".join([c["text"] for c in chunks])
    answer = await asyncio.to_thread(ask_lmstudio, query, context_text)
    await message.answer(answer)
