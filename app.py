from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ai_client import has_api_key, polish_answer
from src.data_loader import load_file, profile_dataset
from src.kpi_engine import answer_question


st.set_page_config(page_title="ProcureAI Insights", page_icon="📊", layout="wide")

st.title("📊 ProcureAI Insights")
st.caption("Chatbot inteligente para consultar KPIs de procurement, finanzas y negocio en lenguaje natural.")

with st.sidebar:
    st.header("Configuración")
    st.write("1. Sube un CSV o Excel.")
    st.write("2. Pregunta por profit, spend, revenue, proveedores o productos.")
    if has_api_key():
        st.success("OpenAI API key detectada: respuestas mejoradas activas.")
    else:
        st.info("Sin API key: la app funciona con respuestas determinísticas. Agrega la key para mejorar el lenguaje.")

uploaded_file = st.file_uploader("Carga tu archivo de datos", type=["csv", "xlsx", "xls"])

if uploaded_file is None:
    st.info("Puedes comenzar usando el archivo de prueba: `data/sample_procurement_data.csv`.")
    st.stop()

try:
    df = load_file(uploaded_file, uploaded_file.name)
    profile = profile_dataset(df)
except Exception as exc:
    st.error(str(exc))
    st.stop()

st.success(f"Archivo cargado correctamente: {profile.rows} filas y {len(profile.columns)} columnas.")

col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("Columnas reconocidas")
    if profile.recognized_columns:
        st.json(profile.recognized_columns)
    else:
        st.warning("No se reconocieron columnas de negocio automáticamente.")
with col2:
    st.subheader("Vista previa")
    st.dataframe(df.head(10), use_container_width=True)

st.divider()
st.subheader("Haz una pregunta")
example_questions = [
    "¿Cuál fue el profit total?",
    "¿Cuál fue el spend total?",
    "¿Qué proveedor tuvo mayor gasto?",
    "¿Cuál fue el revenue total?",
    "¿Cuáles fueron los productos con mejor desempeño?",
]
question = st.text_input("Pregunta en lenguaje natural", placeholder=example_questions[0])
selected_example = st.selectbox("O usa una pregunta de prueba", [""] + example_questions)
final_question = question.strip() or selected_example

if st.button("Analizar", type="primary"):
    if not final_question:
        st.warning("Escribe o selecciona una pregunta para continuar.")
        st.stop()

    result = answer_question(df, profile, final_question)
    with st.spinner("Generando insight..."):
        try:
            answer = polish_answer(result.question, result.answer, result.details)
        except Exception as exc:
            answer = result.answer
            st.warning(f"No se pudo usar OpenAI, se muestra la respuesta calculada localmente. Detalle: {exc}")

    st.markdown("### Respuesta")
    st.write(answer)
    st.markdown("### Detalles calculados")
    st.json({"intent": result.intent, "details": result.details})

st.divider()
st.markdown("#### KPIs rápidos")
quick_cols = st.columns(3)
revenue_col = profile.recognized_columns.get("revenue")
spend_col = profile.recognized_columns.get("spend") or profile.recognized_columns.get("cost")
profit_available = revenue_col and spend_col

with quick_cols[0]:
    st.metric("Revenue", f"${float(df[revenue_col].sum()):,.2f}" if revenue_col else "N/A")
with quick_cols[1]:
    st.metric("Spend", f"${float(df[spend_col].sum()):,.2f}" if spend_col else "N/A")
with quick_cols[2]:
    if profit_available:
        st.metric("Profit", f"${float(df[revenue_col].sum() - df[spend_col].sum()):,.2f}")
    else:
        st.metric("Profit", "N/A")
