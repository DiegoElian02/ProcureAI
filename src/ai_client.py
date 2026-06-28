"""Optional OpenAI helpers for code generation and business-friendly responses."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd
from openai import OpenAI

from src.config import get_secret
from src.data_loader import DatasetProfile


def has_api_key() -> bool:
    """Return True when an OpenAI API key is configured."""
    return bool(get_secret("OPENAI_API_KEY"))


def _client() -> OpenAI:
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY no está configurada.")
    return OpenAI(api_key=api_key)


def _dataset_context(df: pd.DataFrame, profile: DatasetProfile) -> dict[str, Any]:
    return {
        "columns": profile.columns,
        "recognized_columns": profile.recognized_columns,
        "date_columns": profile.date_columns,
        "numeric_columns": profile.numeric_columns,
        "dtypes": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "sample_rows": df.head(8).to_dict(orient="records"),
    }


def generate_analysis_code(question: str, df: pd.DataFrame, profile: DatasetProfile) -> str:
    """Ask OpenAI to generate pandas code that answers the user's question."""
    response = _client().chat.completions.create(
        model=get_secret("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un analista senior de datos para ProcureAI Insights. Genera código pandas para responder "
                    "la pregunta del usuario usando exclusivamente el DataFrame `df` ya cargado y pandas como `pd`. "
                    "No incluyas markdown, explicaciones, imports, lectura/escritura de archivos, llamadas de red, loops, funciones ni clases. "
                    "El código debe asignar obligatoriamente la respuesta final a una variable llamada `result`. "
                    "Opcionalmente asigna un texto ejecutivo breve a una variable llamada `insight` con esta estructura: resultado + interpretación + recomendación. "
                    "Si la pregunta pide gráfica, comparación o tendencia, devuelve en `result` una Serie/DataFrame agrupada lista para graficar. "
                    "Si necesitas fechas, crea columnas temporales en `df` con `pd.to_datetime(..., errors='coerce', format='mixed')`. "
                    "Si calculas profit, usa revenue - cost cuando existan esas columnas; si no existe cost, usa revenue - spend. "
                    "Usa exactamente los nombres de columnas del esquema."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "dataset_context": _dataset_context(df, profile),
                        "valid_examples": [
                            "df['_date'] = pd.to_datetime(df['date'], errors='coerce', format='mixed')\nfiltered = df[df['_date'].dt.month == 3]\nresult = float((filtered['revenue'] - filtered['cost']).sum())\ninsight = f\"El profit filtrado es ${result:,.2f}.\"",
                            "result = df.groupby('provider')['spend'].sum().sort_values(ascending=False).head(5)",
                        ],
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ],
    )
    code = response.choices[0].message.content or ""
    return code.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()


def generate_visualization_code(
    question: str,
    df: pd.DataFrame,
    profile: DatasetProfile,
    analysis_result: Any | None = None,
) -> str:
    """Ask OpenAI to generate pandas code for a question-specific visualization."""
    response = _client().chat.completions.create(
        model=get_secret("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un analista de datos experto en visualización para ProcureAI Insights. "
                    "Genera código pandas que prepare una gráfica directamente relacionada con la pregunta del usuario. "
                    "Usa exclusivamente el DataFrame `df` ya cargado y pandas como `pd`. "
                    "No incluyas markdown, explicaciones, imports, lectura/escritura de archivos, llamadas de red, loops, funciones ni clases. "
                    "El código debe asignar obligatoriamente `chart_data` con una Serie o DataFrame listo para Streamlit. "
                    "También asigna `chart_type` como uno de: 'bar', 'line', 'area' o 'scatter', y `chart_title` con un título breve. "
                    "Si la pregunta pide tendencia o tiempo, usa gráfica line y agrupa por mes/fecha. "
                    "Si pide comparación, ranking, proveedor, producto o categoría, usa gráfica bar y agrupa por la dimensión solicitada. "
                    "Si necesitas fechas, crea columnas temporales con `pd.to_datetime(..., errors='coerce', format='mixed')`. "
                    "Usa exactamente los nombres de columnas del esquema."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "dataset_context": _dataset_context(df, profile),
                        "analysis_result": analysis_result,
                        "valid_examples": [
                            "df['_date'] = pd.to_datetime(df['date'], errors='coerce', format='mixed')\nchart_data = df.groupby(df['_date'].dt.to_period('M').astype(str))['revenue'].sum()\nchart_type = 'line'\nchart_title = 'Revenue mensual'",
                            "chart_data = df.groupby('provider')['spend'].sum().sort_values(ascending=False).head(10)\nchart_type = 'bar'\nchart_title = 'Top proveedores por spend'",
                        ],
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ],
    )
    code = response.choices[0].message.content or ""
    return code.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()


def create_query_plan(question: str, df: pd.DataFrame, profile: DatasetProfile) -> dict[str, Any]:
    """Ask OpenAI to convert a natural-language question into a safe JSON query plan."""
    response = _client().chat.completions.create(
        model=get_secret("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un analista de datos para ProcureAI Insights. Convierte la pregunta del usuario "
                    "en un plan JSON seguro para pandas. No escribas código Python. Solo devuelve JSON válido. "
                    "Métricas permitidas: profit, spend, spend_by_provider, revenue, top_products, general_summary. "
                    "Filtros permitidos dentro de filters: month como número 1-12, year como número, start_date YYYY-MM-DD, end_date YYYY-MM-DD. "
                    "group_by permitido: provider, product, category. top_n permitido como entero. "
                    "Si preguntan 'marzo', usa filters.month = 3. Si no mencionan año, omite year."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "dataset_schema": _dataset_context(df, profile),
                        "expected_json_example": {
                            "metric": "profit",
                            "filters": {"month": 3},
                            "group_by": None,
                            "top_n": None,
                        },
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ],
    )
    content = response.choices[0].message.content or "{}"
    plan = json.loads(content)
    if not isinstance(plan, dict):
        raise ValueError("OpenAI no devolvió un plan JSON válido.")
    return plan


def polish_answer(question: str, deterministic_answer: str, details: dict[str, Any]) -> str:
    """Use OpenAI to rewrite the calculated output as a concise executive insight."""
    response = _client().chat.completions.create(
        model=get_secret("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres ProcureAI Insights, un asistente ejecutivo de procurement y finanzas. "
                    "Responde en español, breve, claro y accionable. No inventes datos. "
                    "Respeta exactamente los números, tablas, filtros y detalles calculados. "
                    "Usa una estructura consistente de máximo 4 líneas: Respuesta directa, Insight de negocio y Recomendación accionable."
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
                    default=str,
                ),
            },
        ],
    )
    return response.choices[0].message.content or deterministic_answer
