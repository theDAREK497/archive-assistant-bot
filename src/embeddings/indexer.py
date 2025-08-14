import os
import pickle
import faiss
from pathlib import Path
from src.embeddings.provider import get_embedding

INDEX_PATH = Path("src/storage/index.faiss")
META_PATH = Path("src/storage/meta.pkl")

def build_index(chunks_dir="src/storage/files/chunks"):
    print("[INDEX] Building FAISS index...")
    vectors = []
    metadata = []

    chunk_dir = Path(chunks_dir)
    files = list(chunk_dir.glob("*.txt"))
    if not files:
        print("[INDEX] No chunks found.")
        return

    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        emb = get_embedding(text)
        if emb:
            vectors.append(emb)
            metadata.append({
                "file": file_path.name,
                "text": text
            })

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
    import numpy as np
    if not INDEX_PATH.exists() or not META_PATH.exists():
        print("[SEARCH] No index found. Please build index first.")
        return []

    index = faiss.read_index(str(INDEX_PATH))
    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)

    query_emb = get_embedding(query)
    if not query_emb:
        return []

    D, I = index.search(np.array([query_emb]).astype("float32"), top_k)
    results = []
    for idx in I[0]:
        results.append(metadata[idx])
    return results

if __name__ == "__main__":
    import numpy as np
    build_index()
    print(search("Что вы можете сделать для ритейлеров?"))
