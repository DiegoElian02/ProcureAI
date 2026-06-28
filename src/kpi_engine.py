"""KPI calculations and safe query-plan execution for ProcureAI Insights."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.data_loader import DatasetProfile


MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


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


def build_rule_based_plan(question: str) -> dict[str, Any]:
    """Create a simple local query plan when OpenAI is not available."""
    q = question.lower()
    plan: dict[str, Any] = {"metric": interpret_intent(question), "filters": {}}

    for month_name, month_number in MONTHS.items():
        if month_name in q:
            plan["filters"]["month"] = month_number
            break

    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", q)
    if year_match:
        plan["filters"]["year"] = int(year_match.group(1))

    if plan["metric"] == "spend_by_provider":
        plan["group_by"] = "provider"
    elif plan["metric"] == "top_products":
        plan["group_by"] = "product"
        plan["top_n"] = 5

    return plan


def _date_filtered_df(df: pd.DataFrame, profile: DatasetProfile, filters: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    date_col = profile.recognized_columns.get("date") or (profile.date_columns[0] if profile.date_columns else None)
    applied: dict[str, Any] = {}
    filtered = df

    if not date_col or not filters:
        return filtered, applied

    dates = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    mask = pd.Series(True, index=df.index)

    month = filters.get("month")
    if month:
        mask &= dates.dt.month == int(month)
        applied["month"] = int(month)

    year = filters.get("year")
    if year:
        mask &= dates.dt.year == int(year)
        applied["year"] = int(year)

    start_date = filters.get("start_date")
    if start_date:
        start = pd.to_datetime(start_date, errors="coerce")
        if pd.notna(start):
            mask &= dates >= start
            applied["start_date"] = str(start.date())

    end_date = filters.get("end_date")
    if end_date:
        end = pd.to_datetime(end_date, errors="coerce")
        if pd.notna(end):
            mask &= dates <= end
            applied["end_date"] = str(end.date())

    return filtered.loc[mask], applied


def _period_label(applied_filters: dict[str, Any]) -> str:
    if not applied_filters:
        return "total"
    parts = []
    month = applied_filters.get("month")
    if month:
        month_name = next((name for name, number in MONTHS.items() if number == month and name in MONTHS), str(month))
        parts.append(f"del mes de {month_name}")
    if applied_filters.get("year"):
        parts.append(f"del año {applied_filters['year']}")
    if applied_filters.get("start_date") or applied_filters.get("end_date"):
        parts.append(f"entre {applied_filters.get('start_date', 'inicio')} y {applied_filters.get('end_date', 'fin')}")
    return " ".join(parts)


def calculate_profit(df: pd.DataFrame, profile: DatasetProfile) -> float | None:
    revenue_col = profile.recognized_columns.get("revenue")
    cost_col = profile.recognized_columns.get("cost") or profile.recognized_columns.get("spend")
    if not revenue_col or not cost_col:
        return None
    return float(df[revenue_col].sum() - df[cost_col].sum())


def answer_question(
    df: pd.DataFrame,
    profile: DatasetProfile,
    question: str,
    query_plan: dict[str, Any] | None = None,
) -> KPIResult:
    """Answer procurement KPI questions using a safe, structured query plan."""
    plan = query_plan or build_rule_based_plan(question)
    allowed_metrics = {"profit", "spend", "spend_by_provider", "revenue", "top_products", "general_summary"}
    intent = str(plan.get("metric") or interpret_intent(question))
    if intent not in allowed_metrics:
        intent = interpret_intent(question)

    raw_filters = plan.get("filters", {}) if isinstance(plan, dict) else {}
    filters = raw_filters if isinstance(raw_filters, dict) else {}
    recognized = profile.recognized_columns
    details: dict[str, object] = {"query_plan": plan}

    filtered_df, applied_filters = _date_filtered_df(df, profile, filters)
    details["filters_applied"] = applied_filters
    details["rows_analyzed"] = int(len(filtered_df))
    period_label = _period_label(applied_filters)

    if filtered_df.empty:
        return KPIResult(
            question=question,
            intent=intent,
            answer="No encontré registros que cumplan con los filtros solicitados.",
            details=details,
        )

    if intent == "profit":
        profit = calculate_profit(filtered_df, profile)
        if profit is None:
            answer = "No pude calcular profit porque faltan columnas de revenue y cost/spend."
        else:
            details["profit"] = round(profit, 2)
            answer = f"El profit {period_label} es ${profit:,.2f}. Esto indica el valor generado después de restar costos o gasto a los ingresos."

    elif intent == "spend_by_provider":
        spend_col = recognized.get("spend") or recognized.get("cost")
        provider_col = recognized.get("provider")
        if not spend_col or not provider_col:
            answer = "No pude agrupar el gasto por proveedor porque faltan columnas de spend/cost o provider."
        else:
            grouped = filtered_df.groupby(provider_col, dropna=False)[spend_col].sum().sort_values(ascending=False)
            top_provider = grouped.index[0]
            top_value = float(grouped.iloc[0])
            details["spend_by_provider"] = grouped.round(2).to_dict()
            answer = f"El proveedor con mayor gasto {period_label} es {top_provider} con ${top_value:,.2f}. Este proveedor concentra la mayor oportunidad de negociación o revisión de contratos."

    elif intent == "spend":
        spend_col = recognized.get("spend") or recognized.get("cost")
        if not spend_col:
            answer = "No encontré una columna de spend o cost para calcular el gasto total."
        else:
            spend = float(filtered_df[spend_col].sum())
            details["spend"] = round(spend, 2)
            answer = f"El spend {period_label} es ${spend:,.2f}. Este monto representa la base principal para analizar ahorros y eficiencia de procurement."

    elif intent == "revenue":
        revenue_col = recognized.get("revenue")
        if not revenue_col:
            answer = "No encontré una columna de revenue/sales para calcular ingresos."
        else:
            revenue = float(filtered_df[revenue_col].sum())
            details["revenue"] = round(revenue, 2)
            answer = f"El revenue {period_label} es ${revenue:,.2f}. Es una señal directa del volumen de negocio generado por los registros cargados."

    elif intent == "top_products":
        product_col = recognized.get("product")
        revenue_col = recognized.get("revenue")
        if not product_col or not revenue_col:
            answer = "No pude identificar productos destacados porque faltan columnas de product o revenue."
        else:
            top_n = int(plan.get("top_n") or 5)
            grouped = filtered_df.groupby(product_col, dropna=False)[revenue_col].sum().sort_values(ascending=False).head(top_n)
            details["top_products"] = grouped.round(2).to_dict()
            leader = grouped.index[0]
            answer = f"El producto con mejor desempeño por revenue {period_label} es {leader} con ${float(grouped.iloc[0]):,.2f}. Conviene revisar si puede escalarse o replicarse su estrategia comercial."

    else:
        profit = calculate_profit(filtered_df, profile)
        spend_col = recognized.get("spend") or recognized.get("cost")
        revenue_col = recognized.get("revenue")
        metrics = []
        if revenue_col:
            metrics.append(f"revenue ${float(filtered_df[revenue_col].sum()):,.2f}")
        if spend_col:
            metrics.append(f"spend ${float(filtered_df[spend_col].sum()):,.2f}")
        if profit is not None:
            metrics.append(f"profit ${profit:,.2f}")
        answer = f"Resumen {period_label}: " + ", ".join(metrics) + ". Puedes preguntar por profit, spend, revenue o gasto por proveedor."
        details["available_metrics"] = metrics

    return KPIResult(question=question, intent=intent, answer=answer, details=details)
