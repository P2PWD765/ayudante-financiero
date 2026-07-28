"""
Funciones auxiliares reutilizables.

Incluye utilidades de fechas, validación, formato numérico y colores.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

import pandas as pd


def parse_date(value: str | datetime | pd.Timestamp) -> pd.Timestamp:
    """Convierte un valor a Timestamp de pandas.

    Args:
        value: Fecha como texto, datetime o Timestamp.

    Returns:
        Fecha normalizada como pd.Timestamp.

    Raises:
        ValueError: Si el valor no se puede interpretar como fecha.
    """
    try:
        return pd.Timestamp(value)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"No se pudo interpretar la fecha: {value}") from exc


def validate_tickers(tickers: Iterable[str]) -> list[str]:
    """Limpia y valida una lista de tickers.

    Args:
        tickers: Iterable de símbolos (ej. ['AAPL', ' msft ']).

    Returns:
        Lista de tickers en mayúsculas, sin vacíos ni duplicados.

    Raises:
        ValueError: Si no queda ningún ticker válido.
    """
    cleaned: list[str] = []
    seen: set[str] = set()

    for raw in tickers:
        ticker = str(raw).strip().upper()
        if not ticker or ticker in seen:
            continue
        cleaned.append(ticker)
        seen.add(ticker)

    if not cleaned:
        raise ValueError("Debes indicar al menos un ticker válido.")

    return cleaned


def weights_sum_to_one(weights: Iterable[float], tolerance: float = 1e-6) -> bool:
    """Indica si los pesos suman aproximadamente 1.

    Args:
        weights: Pesos del portafolio.
        tolerance: Tolerancia numérica permitida.

    Returns:
        True si la suma está dentro de la tolerancia.
    """
    total = float(sum(weights))
    return abs(total - 1.0) <= tolerance


def format_percent(value: float | None, decimals: int = 2) -> str:
    """Formatea un número como porcentaje.

    Args:
        value: Valor en forma decimal (0.15 -> 15%).
        decimals: Decimales a mostrar.

    Returns:
        Texto formateado o 'N/A' si el valor es None/NaN.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def format_labeled(
    value: float | None,
    kind: str = "percent",
    label: str | None = None,
    decimals: int = 2,
) -> str:
    """Formatea un valor y le añade una etiqueta corta (ej. '13.33% · retorno').

    Args:
        value: Número a formatear.
        kind: 'percent' | 'number' | 'ratio' | 'compact'.
        label: Texto indicador (ej. 'riesgo anual', 'retorno esperado').
        decimals: Decimales.

    Returns:
        Cadena legible para UI.
    """
    if kind == "percent":
        formatted = format_percent(value, decimals)
    elif kind == "compact":
        formatted = format_compact(value, decimals)
    elif kind == "ratio":
        if value is None or (isinstance(value, float) and pd.isna(value)):
            formatted = "N/A"
        else:
            formatted = f"{value:.{decimals}f}"
    else:
        formatted = format_number(value, decimals)

    if not label or formatted == "N/A":
        return formatted
    return f"{formatted} · {label}"


# Glosario corto para tooltips (help=) de métricas y captions.
INDICATOR_HELP: dict[str, str] = {
    "rf": (
        "Tasa libre de riesgo anual (Rf). Es el rendimiento de un activo "
        "sin riesgo (ej. bono del Tesoro). Se usa en Sharpe, Treynor y Jensen."
    ),
    "activos": "Cantidad de tickers incluidos en el análisis actual.",
    "periodo": "Ventana histórica de precios descargados de Yahoo Finance.",
    "benchmark": "Índice de referencia para Beta y Alpha (por defecto S&P 500).",
    "riesgo_anual": (
        "Riesgo / volatilidad anual (σ): desviación estándar de los retornos "
        "mensuales, anualizada × √12. Mide cuánto puede variar el portafolio."
    ),
    "riesgo_mensual": (
        "Riesgo / volatilidad mensual (σ): desviación estándar de los "
        "retornos log mensuales."
    ),
    "retorno_anual": (
        "Retorno / rendimiento esperado anual: media de retornos mensuales × 12. "
        "No es un cambio respecto a otro periodo; es el rendimiento medio estimado."
    ),
    "retorno_mensual": (
        "Retorno / rendimiento esperado mensual: media de los retornos log mensuales."
    ),
    "sharpe": (
        "Ratio de Sharpe anual: (Retorno − Rf) / Riesgo. "
        "Cuanto más alto, mejor rendimiento por unidad de riesgo."
    ),
    "beta": (
        "Beta: sensibilidad al benchmark. β=1 se mueve igual que el mercado; "
        ">1 más volátil; <1 menos volátil."
    ),
    "treynor": (
        "Ratio de Treynor: (Retorno − Rf) / Beta. "
        "Rendimiento extra por unidad de riesgo sistemático."
    ),
    "jensen": (
        "Alpha de Jensen: retorno extra frente al CAPM. "
        "Positivo = el portafolio superó lo esperado según su Beta."
    ),
    "var": (
        "VaR paramétrico 95%: pérdida estimada en un mes malo "
        "(aproximación normal con media y σ)."
    ),
    "peso": "Porcentaje del capital asignado a ese activo (los pesos suman 100%).",
    "correlacion": (
        "Correlación (−1 a +1): qué tan juntos se mueven dos activos. "
        "Verde = positiva; rojo = negativa; cerca de 0 = poco relacionados."
    ),
    "covarianza": (
        "Covarianza mensual: mide cómo covarían los retornos de dos activos. "
        "Base para riesgo del portafolio."
    ),
    "capital": "Monto de dinero del portafolio usado en VaR y valuación de pesos.",
}


def show_metric(
    label: str,
    value: Any,
    *,
    help_key: str | None = None,
    help_text: str | None = None,
    delta: str | None = None,
    delta_color: str = "off",
) -> None:
    """Muestra un st.metric con tooltip explicativo.

    Args:
        label: Título visible del indicador.
        value: Valor principal (ya formateado o número).
        help_key: Clave en INDICATOR_HELP.
        help_text: Texto de ayuda libre (prioridad sobre help_key).
        delta: Texto secundario (ej. 'Retorno esperado: 13%'). Usa delta_color='off'
            para no interpretarlo como variación temporal.
        delta_color: 'off' | 'normal' | 'inverse'.
    """
    import streamlit as st

    tip = help_text or (INDICATOR_HELP.get(help_key) if help_key else None)
    kwargs: dict[str, Any] = {"label": label, "value": value}
    if tip:
        kwargs["help"] = tip
    if delta is not None:
        kwargs["delta"] = delta
        kwargs["delta_color"] = delta_color
    st.metric(**kwargs)


def format_number(value: float | None, decimals: int = 2) -> str:
    """Formatea un número con separador de miles.

    Args:
        value: Número a formatear.
        decimals: Decimales a mostrar.

    Returns:
        Texto formateado o 'N/A' si el valor es None/NaN.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    return f"{value:,.{decimals}f}"


def format_compact(value: float | None, decimals: int = 2) -> str:
    """Formatea montos grandes de forma compacta (K, M, B, T).

    Args:
        value: Monto numérico.
        decimals: Decimales a mostrar.

    Returns:
        Texto compacto o 'N/A'.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"

    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    for threshold, suffix in (
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    ):
        if abs_value >= threshold:
            return f"{sign}{abs_value / threshold:.{decimals}f}{suffix}"

    return f"{sign}{abs_value:.{decimals}f}"


def safe_get(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Obtiene un valor de un diccionario de forma segura.

    Args:
        data: Diccionario de origen.
        key: Clave buscada.
        default: Valor por defecto si no existe o es None.

    Returns:
        Valor encontrado o default.
    """
    value = data.get(key, default)
    return default if value is None else value


def apply_theme() -> None:
    """Inyecta CSS de la paleta Azul Dashboard en la página Streamlit.

    Debe llamarse en app.py y en cada página de pages/, justo después
    de st.set_page_config / al inicio del script.
    """
    import streamlit as st

    import config

    c = config.COLORS
    st.markdown(
        f"""
        <style>
        :root {{
            --af-bg: {c["background"]};
            --af-card: {c["card"]};
            --af-text: {c["text"]};
            --af-muted: {c["text_muted"]};
            --af-primary: {c["primary"]};
            --af-soft: {c["primary_soft"]};
            --af-secondary: {c["secondary"]};
            --af-danger: {c["danger"]};
            --af-on-primary: {c["on_primary"]};
        }}

        html, body, [data-testid="stAppViewContainer"],
        .stApp, [data-testid="stApp"] {{
            background-color: var(--af-bg) !important;
            color: var(--af-text) !important;
        }}

        [data-testid="stSidebar"],
        [data-testid="stSidebar"] > div:first-child {{
            background-color: var(--af-card) !important;
            border-right: 3px solid var(--af-primary) !important;
        }}

        [data-testid="stHeader"] {{
            background-color: var(--af-card) !important;
            border-bottom: 3px solid var(--af-primary) !important;
        }}

        h1, h2, h3, h4, h5, h6, p, label,
        .stMarkdown, .stCaption, [data-testid="stWidgetLabel"] {{
            color: var(--af-text) !important;
        }}

        .stCaption, [data-testid="stCaptionContainer"] {{
            color: var(--af-muted) !important;
        }}

        [data-testid="stMetric"],
        [data-testid="stExpander"],
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: var(--af-card) !important;
            border: 1px solid var(--af-soft) !important;
            border-radius: 8px !important;
        }}

        [data-testid="stMetric"] {{
            padding: 0.75rem 1rem !important;
        }}

        [data-testid="stMetricValue"] {{
            color: var(--af-primary) !important;
        }}

        [data-testid="stMetricLabel"] {{
            color: var(--af-muted) !important;
        }}

        .stButton > button[kind="primary"],
        button[data-testid="baseButton-primary"] {{
            background-color: var(--af-primary) !important;
            color: var(--af-on-primary) !important;
            border: 1px solid var(--af-primary) !important;
        }}

        .stButton > button[kind="secondary"],
        button[data-testid="baseButton-secondary"] {{
            background-color: var(--af-card) !important;
            color: var(--af-text) !important;
            border: 1px solid var(--af-primary) !important;
        }}

        .stTextInput input, .stNumberInput input,
        .stSelectbox div[data-baseweb="select"] {{
            background-color: var(--af-card) !important;
            color: var(--af-text) !important;
        }}

        /* Tablas Streamlit */
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {{
            border: 1px solid var(--af-soft) !important;
            border-radius: 8px !important;
        }}

        [data-testid="stAlert"] {{
            border-left: 4px solid var(--af-primary) !important;
            color: var(--af-text) !important;
        }}

        /* Tabs */
        button[data-baseweb="tab"] {{
            color: var(--af-muted) !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: var(--af-primary) !important;
            border-bottom-color: var(--af-primary) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def theme_styler(styler: Any, format_dict: dict | str | None = None, na_rep: str = "N/A") -> Any:
    """Aplica formato y colores de tabla (headers azul, texto oscuro legible).

    Args:
        styler: pd.DataFrame o Styler de pandas.
        format_dict: Dict de formato por columna, o un string único (ej. "{:.2%}").
        na_rep: Texto para valores nulos.

    Returns:
        Styler listo para st.dataframe.
    """
    import config

    c = config.COLORS

    if hasattr(styler, "style"):
        # Es un DataFrame
        out = styler.style
    else:
        out = styler

    if isinstance(format_dict, dict):
        out = out.format(format_dict, na_rep=na_rep)
    elif isinstance(format_dict, str):
        out = out.format(format_dict, na_rep=na_rep)

    return (
        out.set_properties(
            **{
                "color": c["text"],
                "background-color": c["card"],
                "border-color": c["primary_soft"],
            }
        )
        .set_table_styles(
            [
                {
                    "selector": "th",
                    "props": [
                        ("background-color", c["primary"]),
                        ("color", c["on_primary"]),
                        ("font-weight", "600"),
                        ("text-align", "center"),
                        ("border", f"1px solid {c['primary']}"),
                    ],
                },
                {
                    "selector": "td",
                    "props": [
                        ("color", c["text"]),
                        ("background-color", c["card"]),
                        ("text-align", "right"),
                        ("border", f"1px solid {c['primary_soft']}"),
                    ],
                },
                {
                    "selector": "tr:nth-child(even) td",
                    "props": [
                        ("background-color", c["primary_soft"]),
                        ("color", c["text"]),
                    ],
                },
                {
                    "selector": "tr:hover td",
                    "props": [
                        ("background-color", "#BFDBFE"),
                        ("color", c["text"]),
                    ],
                },
            ]
        )
    )