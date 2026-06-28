"""Simple Streamlit visualizations for KPI analysis results."""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.data_loader import DatasetProfile


_CHART_KEYWORDS = ("gráfica", "grafica", "chart", "tendencia", "trend", "comparación", "comparacion", "por mes", "por proveedor")


def question_requests_chart(question: str) -> bool:
    """Return True if the user explicitly asks for a chart or comparison/trend."""
    q = question.lower()
    return any(keyword in q for keyword in _CHART_KEYWORDS)


def render_quick_charts(df: pd.DataFrame, profile: DatasetProfile) -> None:
    """Render baseline trend/comparison charts when the required columns exist."""
    date_col = profile.recognized_columns.get("date") or (profile.date_columns[0] if profile.date_columns else None)
    revenue_col = profile.recognized_columns.get("revenue")
    spend_col = profile.recognized_columns.get("spend") or profile.recognized_columns.get("cost")
    provider_col = profile.recognized_columns.get("provider")

    chart_tabs = st.tabs(["Tendencia mensual", "Gasto por proveedor"])

    with chart_tabs[0]:
        if date_col and (revenue_col or spend_col):
            chart_df = df.copy()
            chart_df["_month"] = pd.to_datetime(chart_df[date_col], errors="coerce", format="mixed").dt.to_period("M").astype(str)
            values: dict[str, pd.Series] = {}
            if revenue_col:
                values["revenue"] = chart_df.groupby("_month")[revenue_col].sum()
            if spend_col:
                values["spend"] = chart_df.groupby("_month")[spend_col].sum()
            monthly = pd.DataFrame(values).fillna(0)
            if revenue_col and spend_col:
                monthly["profit"] = monthly["revenue"] - monthly["spend"]
            st.line_chart(monthly)
        else:
            st.info("Para generar tendencia mensual se necesita una columna de fecha y al menos revenue o spend/cost.")

    with chart_tabs[1]:
        if provider_col and spend_col:
            provider_spend = df.groupby(provider_col)[spend_col].sum().sort_values(ascending=False).head(10)
            st.bar_chart(provider_spend)
        else:
            st.info("Para comparar gasto por proveedor se necesitan columnas de proveedor y spend/cost.")


def render_result_chart(serialized_output: Any, question: str) -> None:
    """Render a chart for generated-code results when the shape is chartable."""
    if not question_requests_chart(question):
        return

    if isinstance(serialized_output, dict):
        chart_df = pd.DataFrame(
            {"dimension": list(serialized_output.keys()), "value": list(serialized_output.values())}
        ).set_index("dimension")
        st.bar_chart(chart_df)
        return

    if isinstance(serialized_output, list) and serialized_output:
        chart_df = pd.DataFrame(serialized_output)
        numeric_cols = chart_df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            st.bar_chart(chart_df[numeric_cols])


def render_custom_chart(chart_data: Any, chart_type: str, chart_title: str | None = None) -> None:
    """Render custom chart data generated for the user's specific question."""
    if chart_title:
        st.markdown(f"#### {chart_title}")

    if isinstance(chart_data, pd.Series):
        data = chart_data
    elif isinstance(chart_data, pd.DataFrame):
        data = chart_data
    elif isinstance(chart_data, dict):
        data = pd.Series(chart_data)
    elif isinstance(chart_data, list):
        data = pd.DataFrame(chart_data)
    else:
        st.info("El resultado no tiene una forma compatible para graficar.")
        return

    if chart_type == "line":
        st.line_chart(data)
    elif chart_type == "area":
        st.area_chart(data)
    elif chart_type == "scatter":
        st.scatter_chart(data)
    else:
        st.bar_chart(data)


def render_question_fallback_chart(df: pd.DataFrame, profile: DatasetProfile, question: str) -> bool:
    """Render a deterministic chart related to the question when GPT chart code fails."""
    q = question.lower()
    provider_col = profile.recognized_columns.get("provider")
    product_col = profile.recognized_columns.get("product")
    date_col = profile.recognized_columns.get("date") or (profile.date_columns[0] if profile.date_columns else None)
    revenue_col = profile.recognized_columns.get("revenue")
    spend_col = profile.recognized_columns.get("spend") or profile.recognized_columns.get("cost")
    cost_col = profile.recognized_columns.get("cost") or spend_col

    if any(word in q for word in ["rentable", "profit", "ganancia", "utilidad"]) and provider_col and revenue_col and cost_col:
        chart_df = df.copy()
        chart_df["profit"] = chart_df[revenue_col] - chart_df[cost_col]
        st.markdown("#### Profit por proveedor")
        st.bar_chart(chart_df.groupby(provider_col)["profit"].sum().sort_values(ascending=False).head(10))
        return True

    if any(word in q for word in ["proveedor", "supplier", "vendor"]) and provider_col and spend_col:
        st.markdown("#### Spend por proveedor")
        st.bar_chart(df.groupby(provider_col)[spend_col].sum().sort_values(ascending=False).head(10))
        return True

    if any(word in q for word in ["producto", "product"]) and product_col and revenue_col:
        st.markdown("#### Revenue por producto")
        st.bar_chart(df.groupby(product_col)[revenue_col].sum().sort_values(ascending=False).head(10))
        return True

    if any(word in q for word in ["tendencia", "trend", "mes", "mensual", "tiempo"]) and date_col and (revenue_col or spend_col):
        chart_df = df.copy()
        chart_df["_month"] = pd.to_datetime(chart_df[date_col], errors="coerce", format="mixed").dt.to_period("M").astype(str)
        values: dict[str, pd.Series] = {}
        if revenue_col:
            values["revenue"] = chart_df.groupby("_month")[revenue_col].sum()
        if spend_col:
            values["spend"] = chart_df.groupby("_month")[spend_col].sum()
        st.markdown("#### Tendencia mensual")
        st.line_chart(pd.DataFrame(values).fillna(0))
        return True

    return False
