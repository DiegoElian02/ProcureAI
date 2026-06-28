"""Safe-ish execution helpers for OpenAI-generated pandas analysis code."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

import pandas as pd


BLOCKED_NAMES = {
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "setattr",
}

ALLOWED_BUILTINS = {
    "abs": abs,
    "bool": bool,
    "dict": dict,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "round": round,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
}


@dataclass(frozen=True)
class CodeExecutionResult:
    code: str
    result: Any
    insight: str | None


@dataclass(frozen=True)
class VisualizationExecutionResult:
    code: str
    chart_data: Any
    chart_type: str
    chart_title: str | None


def _validate_code(code: str, required_variable: str = "result") -> None:
    """Validate generated code before execution."""
    if "__" in code:
        raise ValueError("El código generado contiene acceso dunder no permitido.")

    tree = ast.parse(code, mode="exec")
    assigns_required_variable = False

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            raise ValueError("El código generado contiene imports, funciones o clases no permitidas.")
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try, ast.Raise)):
            raise ValueError("El código generado contiene control de flujo no permitido.")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ValueError(f"El código generado usa un nombre no permitido: {node.id}.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ValueError("El código generado intenta acceder a atributos privados.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BLOCKED_NAMES:
            raise ValueError(f"El código generado intenta llamar una función no permitida: {node.func.id}.")
        if isinstance(node, ast.Assign):
            assigns_required_variable = assigns_required_variable or any(
                isinstance(target, ast.Name) and target.id == required_variable for target in node.targets
            )

    if not assigns_required_variable:
        raise ValueError(f"El código generado debe asignar la variable `{required_variable}`.")


def execute_analysis_code(df: pd.DataFrame, code: str) -> CodeExecutionResult:
    """Execute validated pandas code against a defensive copy of the uploaded DataFrame."""
    _validate_code(code, required_variable="result")
    local_vars: dict[str, Any] = {"df": df.copy(), "pd": pd, "result": None, "insight": None}
    global_vars = {"__builtins__": ALLOWED_BUILTINS}
    exec(compile(code, "<openai_analysis>", "exec"), global_vars, local_vars)

    result = local_vars.get("result")
    if result is None:
        raise ValueError("El código generado no produjo ningún resultado en `result`.")

    return CodeExecutionResult(code=code, result=result, insight=local_vars.get("insight"))


def execute_visualization_code(df: pd.DataFrame, code: str) -> VisualizationExecutionResult:
    """Execute validated pandas code that prepares chart data for Streamlit."""
    _validate_code(code, required_variable="chart_data")
    local_vars: dict[str, Any] = {
        "df": df.copy(),
        "pd": pd,
        "chart_data": None,
        "chart_type": "bar",
        "chart_title": None,
    }
    global_vars = {"__builtins__": ALLOWED_BUILTINS}
    exec(compile(code, "<openai_visualization>", "exec"), global_vars, local_vars)

    chart_data = local_vars.get("chart_data")
    if chart_data is None:
        raise ValueError("El código generado no produjo datos de gráfica en `chart_data`.")

    chart_type = str(local_vars.get("chart_type") or "bar").lower()
    if chart_type not in {"bar", "line", "area", "scatter"}:
        chart_type = "bar"

    return VisualizationExecutionResult(
        code=code,
        chart_data=chart_data,
        chart_type=chart_type,
        chart_title=local_vars.get("chart_title"),
    )


def serialize_result(result: Any) -> Any:
    """Convert common pandas/numpy objects into Streamlit/JSON-friendly values."""
    if isinstance(result, pd.DataFrame):
        return result.to_dict(orient="records")
    if isinstance(result, pd.Series):
        return result.to_dict()
    if hasattr(result, "item"):
        try:
            return result.item()
        except Exception:
            return str(result)
    return result
