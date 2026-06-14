"""Optional OpenAI-powered wording layer for business-friendly responses."""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from src.config import get_secret


def has_api_key() -> bool:
    """Return True when an OpenAI API key is configured."""
    return bool(get_secret("OPENAI_API_KEY"))


def polish_answer(question: str, deterministic_answer: str, details: dict[str, Any]) -> str:
    """Use OpenAI to rewrite the deterministic KPI output as a concise executive insight."""
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        return deterministic_answer

    client = OpenAI(api_key=api_key)
    model = get_secret("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini"
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres ProcureAI Insights, un asistente ejecutivo de procurement y finanzas. "
                    "Responde en español, breve, claro y accionable. No inventes datos."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "pregunta": question,
                        "respuesta_calculada": deterministic_answer,
                        "detalles": details,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    return response.choices[0].message.content or deterministic_answer
