"""Application configuration helpers."""
from __future__ import annotations

import os
from typing import Optional

import streamlit as st
from dotenv import load_dotenv


load_dotenv()


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Read a setting from Streamlit secrets first, then environment variables."""
    try:
        value = st.secrets.get(name)  # type: ignore[attr-defined]
    except Exception:
        value = None
    return value or os.getenv(name, default)
