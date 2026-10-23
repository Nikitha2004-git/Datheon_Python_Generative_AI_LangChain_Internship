"""Start the app with:  python run.py

Other options:
    python run.py --clean   delete all locally stored vector data (chroma_db/)
    python run.py --check   show whether setup looks correct (never prints keys)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    from app.config import load_settings

    settings = load_settings()
    args = sys.argv[1:]

    if "--clean" in args:
        from app.vector_store import purge_persist_directory

        removed = purge_persist_directory(settings.chroma_dir)
        print(f"Removed {removed} stored document collection(s).")
        return 0

    if "--check" in args:
        print(f"Python:            {sys.version.split()[0]}")
        print(f"Gemini model:      {settings.gemini_model}")
        print(f"Embedding model:   {settings.embedding_model}")
        print(f"API key set:       {'yes' if settings.has_api_key else 'NO - edit .env'}")
        print(f"Chunk size/overlap:{settings.chunk_size}/{settings.chunk_overlap}")
        print(f"Top K:             {settings.top_k}")
        print(f"Max file size:     {settings.max_file_size_mb} MB")
        return 0

    command = [sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "main.py")]
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
