"""Simple launcher:  python run.py   (same as: python -m streamlit run app/main.py)"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    main_file = Path(__file__).resolve().parent / "app" / "main.py"
    raise SystemExit(
        subprocess.call([sys.executable, "-m", "streamlit", "run", str(main_file), *sys.argv[1:]])
    )
