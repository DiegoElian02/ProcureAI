"""Friendly error catalog for user-facing messages."""
from __future__ import annotations


def friendly_error_message(error: Exception | str, context: str = "general") -> str:
    """Translate common technical errors into clear, actionable Spanish messages."""
    message = str(error)
    lower = message.lower()

    if "no está configurada" in lower or "api" in lower and "key" in lower:
        return "No pude usar OpenAI porque falta la API key. Revisa `.streamlit/secrets.toml` o los Secrets de Streamlit Cloud."
    if "formato no soportado" in lower or "extension" in lower:
        return "El archivo no tiene un formato válido. Sube un CSV, XLSX o XLS."
    if "empty" in lower or "no tiene datos" in lower:
        return "El archivo está vacío o no contiene filas analizables. Revisa el archivo y vuelve a cargarlo."
    if "no produjo ningún resultado" in lower or "result" in lower:
        return "No pude obtener un resultado de la consulta. Intenta hacer la pregunta más específica e incluye la métrica que necesitas."
    if "column" in lower or "keyerror" in lower:
        return "La consulta pidió una columna que no existe en el archivo. Revisa los nombres de columnas o pregunta usando las columnas disponibles."
    if "código generado" in lower:
        return "No pude ejecutar de forma segura el análisis generado. Intenta reformular la pregunta con una métrica, periodo o agrupación más clara."

    if context == "question":
        return "No pude procesar la pregunta. Intenta especificar métrica, periodo y agrupación, por ejemplo: 'spend por proveedor en mayo'."
    if context == "file":
        return "No pude procesar el archivo. Verifica que tenga encabezados, filas de datos y columnas numéricas."
    return "Ocurrió un error inesperado. Revisa el archivo o intenta reformular la pregunta."
