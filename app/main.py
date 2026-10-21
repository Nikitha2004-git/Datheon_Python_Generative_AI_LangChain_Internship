"""Application entry point. Start with:  python -m streamlit run app/main.py"""

import sys
from pathlib import Path

# Streamlit puts app/ on sys.path, not the project root; add the root so that
# "from app import ..." works.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.errors import ConfigError  # noqa: E402
from app.ui import render_app  # noqa: E402


def main() -> None:
    import streamlit as st

    try:
        settings = load_settings()
    except ConfigError as exc:
        st.error(exc.user_message)
        st.stop()
        return
    render_app(settings)


if __name__ == "__main__":
    main()
