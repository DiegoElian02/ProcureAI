"""Dataset validation helpers for Sprint 2 acceptance criteria."""
from __future__ import annotations

from dataclasses import dataclass

from src.data_loader import DatasetProfile


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    title: str
    message: str
    recommendation: str


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue]
    recognized_columns: dict[str, str]


def validate_dataset(profile: DatasetProfile) -> ValidationResult:
    """Validate whether the uploaded dataset has enough structure for KPI analysis."""
    issues: list[ValidationIssue] = []
    recognized = profile.recognized_columns
    metric_columns = [column for column in ["revenue", "spend", "cost"] if column in recognized]

    if not profile.numeric_columns:
        issues.append(
            ValidationIssue(
                severity="error",
                title="No se encontraron columnas numéricas",
                message="El archivo necesita al menos una columna numérica para calcular KPIs.",
                recommendation="Agrega columnas como revenue, spend, cost, amount, sales o invoice_amount.",
            )
        )

    if not metric_columns:
        issues.append(
            ValidationIssue(
                severity="error",
                title="Faltan columnas de métricas financieras",
                message="No pude reconocer columnas para revenue, spend o cost.",
                recommendation="Renombra o agrega columnas como revenue/sales/ventas, spend/gasto/amount o cost/costo.",
            )
        )

    if "date" not in recognized and not profile.date_columns:
        issues.append(
            ValidationIssue(
                severity="warning",
                title="No se detectó una columna de fecha",
                message="El análisis total funcionará, pero las tendencias o filtros por periodo pueden fallar.",
                recommendation="Agrega una columna llamada date, fecha, invoice_date u order_date si necesitas análisis temporal.",
            )
        )

    if "provider" not in recognized:
        issues.append(
            ValidationIssue(
                severity="warning",
                title="No se detectó proveedor",
                message="Las comparaciones por proveedor no estarán disponibles automáticamente.",
                recommendation="Agrega o renombra una columna como provider, supplier, vendor o proveedor.",
            )
        )

    has_errors = any(issue.severity == "error" for issue in issues)
    return ValidationResult(is_valid=not has_errors, issues=issues, recognized_columns=recognized)
