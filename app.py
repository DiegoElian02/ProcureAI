from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ai_client import create_query_plan, generate_analysis_code, has_api_key, polish_answer
from src.data_loader import load_file, profile_dataset
from src.code_executor import execute_analysis_code, serialize_result
from src.error_messages import friendly_error_message
from src.kpi_engine import answer_question
from src.validation import validate_dataset
from src.visualizations import render_quick_charts, render_result_chart


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
    st.error(friendly_error_message(exc, context="file"))
    st.stop()

validation = validate_dataset(profile)
if validation.is_valid:
    st.success(f"Archivo cargado correctamente: {profile.rows} filas y {len(profile.columns)} columnas. Validación positiva: el dataset tiene métricas suficientes para analizar.")
else:
    st.error("El archivo fue cargado, pero no tiene las columnas mínimas para analizar KPIs.")

for issue in validation.issues:
    message = f"**{issue.title}:** {issue.message} Recomendación: {issue.recommendation}"
    if issue.severity == "error":
        st.error(message)
    else:
        st.warning(message)

if not validation.is_valid:
    st.stop()

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
        st.warning("Escribe una pregunta accionable. Ejemplo: '¿Cuál fue el spend por proveedor en mayo?' o selecciona una pregunta de prueba.")
        st.stop()

    generated_code = None
    serialized_output = None
    with st.spinner("Generando código, ejecutando análisis y preparando insight..."):
        if has_api_key():
            try:
                generated_code = generate_analysis_code(final_question, df, profile)
                code_result = execute_analysis_code(df, generated_code)
                serialized_output = serialize_result(code_result.result)
                details = {
                    "mode": "openai_generated_pandas_code",
                    "generated_code": generated_code,
                    "raw_result": serialized_output,
                    "insight": code_result.insight,
                }
                base_answer = code_result.insight or f"Resultado calculado: {serialized_output}"
                answer = polish_answer(final_question, base_answer, details)
                result_payload = {"intent": "generated_code", "details": details}
            except Exception as exc:
                st.warning(f"{friendly_error_message(exc, context='question')} Se usará el motor local como respaldo.")
                query_plan = None
                try:
                    query_plan = create_query_plan(final_question, df, profile)
                except Exception:
                    query_plan = None
                result = answer_question(df, profile, final_question, query_plan=query_plan)
                answer = result.answer
                result_payload = {"intent": result.intent, "details": result.details}
        else:
            result = answer_question(df, profile, final_question)
            answer = result.answer
            result_payload = {"intent": result.intent, "details": result.details}

    st.markdown("### Respuesta")
    st.write(answer)

    if generated_code:
        with st.expander("Ver código pandas generado por GPT"):
            st.code(generated_code, language="python")

    if serialized_output is not None:
        st.markdown("### Resultado calculado")
        if isinstance(serialized_output, list):
            st.dataframe(pd.DataFrame(serialized_output), use_container_width=True)
        elif isinstance(serialized_output, dict):
            st.json(serialized_output)
        else:
            st.write(serialized_output)

        st.markdown("### Visualización del resultado")
        render_result_chart(serialized_output, final_question)

    st.markdown("### Detalles calculados")
    st.json(result_payload)

st.divider()
st.markdown("#### Gráficas rápidas")
render_quick_charts(df, profile)

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
