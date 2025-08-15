import os
import pickle
import faiss
import numpy as np
import json
from pathlib import Path
from tqdm import tqdm
from src.embeddings.provider import get_embeddings

# Константы путей
INDEX_PATH = Path("src/storage/index.faiss")
META_PATH = Path("src/storage/meta.pkl")
BATCH_SIZE = 32  # Оптимальный размер батча

def build_index(chunks_dir="src/storage/files/chunks"):
    """Построение FAISS индекса из текстовых чанков"""
    print("[INDEX] Building FAISS index...")
    vectors = []
    metadata = []

    chunk_dir = Path(chunks_dir)
    files = list(chunk_dir.glob("*.txt"))
    if not files:
        print("[INDEX] No chunks found.")
        return

    # Загрузка маппинга URL с обработкой ошибок
    url_mapping = {}
    mapping_file = Path("src/storage/files/url_mapping.json")
    if mapping_file.exists():
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                url_mapping = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"[ERROR] Invalid mapping file: {str(e)}")
            url_mapping = {}

    # Сбор текстов и метаданных
    texts = []
    for file_path in tqdm(files, desc="Processing chunks"):
        try:
            text = file_path.read_text(encoding="utf-8")
            texts.append(text)
            
            # Извлечение оригинального имени файла
            if "_chunk" in file_path.stem:
                original_filename = file_path.stem.rsplit("_chunk", 1)[0] + ".html"
            else:
                original_filename = file_path.stem + ".html"
                
            # Получение URL из маппинга
            url_entry = url_mapping.get(original_filename)
            final_url = "unknown_url"
            
            if isinstance(url_entry, dict):
                final_url = url_entry.get("final_url", "unknown_url")
            elif isinstance(url_entry, str):
                final_url = url_entry
            
            metadata.append({
                "file": file_path.name,
                "text": text,
                "url": final_url
            })
        except Exception as e:
            print(f"[ERROR] Processing {file_path.name}: {str(e)}")

    if not texts:
        print("[INDEX] No texts to process")
        return

    # Генерация эмбеддингов батчами
    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Embedding"):
        batch = texts[i:i+BATCH_SIZE]
        try:
            batch_embs = get_embeddings(batch)
            if batch_embs:
                vectors.extend(batch_embs)
        except Exception as e:
            print(f"[ERROR] Embedding batch {i//BATCH_SIZE}: {str(e)}")

    if not vectors:
        print("[INDEX] No embeddings generated.")
        return

    # Создание и сохранение индекса
    dim = len(vectors[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(vectors).astype("float32"))

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    
    with open(META_PATH, "wb") as f:
        pickle.dump(metadata, f)

    print(f"[INDEX] Saved index with {len(vectors)} vectors.")

def search(query: str, top_k=4):
    """Поиск по индексу"""
    if not INDEX_PATH.exists() or not META_PATH.exists():
        print("[SEARCH] No index found. Please build index first.")
        return []

    try:
        index = faiss.read_index(str(INDEX_PATH))
        with open(META_PATH, "rb") as f:
            metadata = pickle.load(f)

        query_emb = get_embeddings([query])
        if not query_emb:
            return []

        D, I = index.search(np.array(query_emb).astype("float32"), top_k)
        return [metadata[idx] for idx in I[0]]
    except Exception as e:
        print(f"[SEARCH ERROR] {str(e)}")
        return []

if __name__ == "__main__":
    build_index()
    print(search("Что вы можете сделать для ритейлеров?"))