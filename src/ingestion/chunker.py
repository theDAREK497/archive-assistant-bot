from pathlib import Path

TXT_DIR = Path(__file__).resolve().parent.parent / "storage" / "files"

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100):
    """
    Разбивает текст на чанки фиксированного размера (символов) с перекрытием.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def process_all_txt():
    for txt_file in TXT_DIR.glob("*.txt"):
        text = txt_file.read_text(encoding="utf-8")
        chunks = chunk_text(text)
        chunk_dir = TXT_DIR / "chunks"
        chunk_dir.mkdir(exist_ok=True)
        for i, chunk in enumerate(chunks):
            chunk_path = chunk_dir / f"{txt_file.stem}_chunk{i}.txt"
            chunk_path.write_text(chunk, encoding="utf-8")
        print(f"[CHUNK] {txt_file.name} -> {len(chunks)} chunks")

if __name__ == "__main__":
    process_all_txt()
