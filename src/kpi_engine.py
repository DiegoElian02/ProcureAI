"""Rule-based KPI calculations and intent interpretation for ProcureAI Insights."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.data_loader import DatasetProfile


@dataclass(frozen=True)
class KPIResult:
    question: str
    intent: str
    answer: str
    details: dict[str, object]


def interpret_intent(question: str) -> str:
    """Identify the main metric requested by the user using simple keywords."""
    q = question.lower()
    if any(word in q for word in ["profit", "ganancia", "utilidad", "margen"]):
        return "profit"
    if any(word in q for word in ["spend", "gasto", "compras", "proveedor", "supplier", "vendor"]):
        return "spend_by_provider" if any(word in q for word in ["proveedor", "supplier", "vendor", "provider"]) else "spend"
    if any(word in q for word in ["revenue", "venta", "ventas", "ingreso", "ingresos", "sales"]):
        return "revenue"
    if any(word in q for word in ["producto", "product", "desempeño", "performance", "top"]):
        return "top_products"
    return "general_summary"


def calculate_profit(df: pd.DataFrame, profile: DatasetProfile) -> float | None:
    revenue_col = profile.recognized_columns.get("revenue")
    cost_col = profile.recognized_columns.get("cost") or profile.recognized_columns.get("spend")
    if not revenue_col or not cost_col:
        return None
    return float(df[revenue_col].sum() - df[cost_col].sum())


def answer_question(df: pd.DataFrame, profile: DatasetProfile, question: str) -> KPIResult:
    """Answer common procurement KPI questions with deterministic calculations."""
    intent = interpret_intent(question)
    recognized = profile.recognized_columns
    details: dict[str, object] = {}

    if intent == "profit":
        profit = calculate_profit(df, profile)
        if profit is None:
            answer = "No pude calcular profit porque faltan columnas de revenue y cost/spend."
        else:
            details["profit"] = round(profit, 2)
            answer = f"El profit total estimado es ${profit:,.2f}. Esto indica el valor generado después de restar costos o gasto a los ingresos."

    elif intent == "spend_by_provider":
        spend_col = recognized.get("spend") or recognized.get("cost")
        provider_col = recognized.get("provider")
        if not spend_col or not provider_col:
            answer = "No pude agrupar el gasto por proveedor porque faltan columnas de spend/cost o provider."
        else:
            grouped = df.groupby(provider_col, dropna=False)[spend_col].sum().sort_values(ascending=False)
            top_provider = grouped.index[0]
            top_value = float(grouped.iloc[0])
            details["spend_by_provider"] = grouped.round(2).to_dict()
            answer = f"El proveedor con mayor gasto es {top_provider} con ${top_value:,.2f}. Este proveedor concentra la mayor oportunidad de negociación o revisión de contratos."

    elif intent == "spend":
        spend_col = recognized.get("spend") or recognized.get("cost")
        if not spend_col:
            answer = "No encontré una columna de spend o cost para calcular el gasto total."
        else:
            spend = float(df[spend_col].sum())
            details["spend"] = round(spend, 2)
            answer = f"El spend total es ${spend:,.2f}. Este monto representa la base principal para analizar ahorros y eficiencia de procurement."

    elif intent == "revenue":
        revenue_col = recognized.get("revenue")
        if not revenue_col:
            answer = "No encontré una columna de revenue/sales para calcular ingresos."
        else:
            revenue = float(df[revenue_col].sum())
            details["revenue"] = round(revenue, 2)
            answer = f"El revenue total es ${revenue:,.2f}. Es una señal directa del volumen de negocio generado por los registros cargados."

    elif intent == "top_products":
        product_col = recognized.get("product")
        revenue_col = recognized.get("revenue")
        if not product_col or not revenue_col:
            answer = "No pude identificar productos destacados porque faltan columnas de product o revenue."
        else:
            grouped = df.groupby(product_col, dropna=False)[revenue_col].sum().sort_values(ascending=False).head(5)
            details["top_products"] = grouped.round(2).to_dict()
            leader = grouped.index[0]
            answer = f"El producto con mejor desempeño por revenue es {leader} con ${float(grouped.iloc[0]):,.2f}. Conviene revisar si puede escalarse o replicarse su estrategia comercial."

    else:
        profit = calculate_profit(df, profile)
        spend_col = recognized.get("spend") or recognized.get("cost")
        revenue_col = recognized.get("revenue")
        metrics = []
        if revenue_col:
            metrics.append(f"revenue ${float(df[revenue_col].sum()):,.2f}")
        if spend_col:
            metrics.append(f"spend ${float(df[spend_col].sum()):,.2f}")
        if profit is not None:
            metrics.append(f"profit ${profit:,.2f}")
        answer = "Resumen del dataset: " + ", ".join(metrics) + ". Puedes preguntar por profit, spend, revenue o gasto por proveedor."
        details["available_metrics"] = metrics

    return KPIResult(question=question, intent=intent, answer=answer, details=details)
