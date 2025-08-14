import os
import pickle
import faiss
import numpy as np
from pathlib import Path
from tqdm import tqdm
from src.embeddings.provider import get_embeddings

INDEX_PATH = Path("src/storage/index.faiss")
META_PATH = Path("src/storage/meta.pkl")
BATCH_SIZE = 32  # Оптимальный размер батча

def build_index(chunks_dir="src/storage/files/chunks"):
    print("[INDEX] Building FAISS index with batching...")
    vectors = []
    metadata = []

    chunk_dir = Path(chunks_dir)
    files = list(chunk_dir.glob("*.txt"))
    if not files:
        print("[INDEX] No chunks found.")
        return

    # Сбор текстов и метаданных
    texts = []
    for file_path in tqdm(files, desc="Reading chunks"):
        text = file_path.read_text(encoding="utf-8")
        texts.append(text)
        metadata.append({"file": file_path.name, "text": text})
    
    # Обработка батчами
    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Embedding"):
        batch = texts[i:i+BATCH_SIZE]
        batch_embs = get_embeddings(batch)
        vectors.extend(batch_embs)

    if not vectors:
        print("[INDEX] No embeddings generated.")
        return

    dim = len(vectors[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(vectors).astype("float32"))

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    
    with open(META_PATH, "wb") as f:
        pickle.dump(metadata, f)

    print(f"[INDEX] Saved {len(vectors)} vectors.")

def search(query: str, top_k=4):
    if not INDEX_PATH.exists() or not META_PATH.exists():
        print("[SEARCH] No index found. Please build index first.")
        return []

    index = faiss.read_index(str(INDEX_PATH))
    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)

    query_emb = get_embeddings([query])
    if not query_emb:
        return []

    D, I = index.search(np.array(query_emb).astype("float32"), top_k)
    return [metadata[i] for i in I[0]]

if __name__ == "__main__":
    build_index()
    print(search("Что вы можете сделать для ритейлеров?"))