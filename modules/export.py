"""
Exportación de resultados del Dashboard Financiero.

v1: Excel (.xlsx) y CSV.
Futuro: PDF / PowerPoint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from modules.portfolio import portfolios_summary_table


def export_dataframe_to_csv(
    data: pd.DataFrame,
    filepath: str | Path,
    index: bool = True,
) -> Path:
    """Exporta un DataFrame a CSV.

    Args:
        data: Tabla a exportar.
        filepath: Ruta del archivo .csv.
        index: Si True, incluye el índice.

    Returns:
        Path del archivo generado.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=index, encoding="utf-8-sig")
    return path


def export_dataframes_to_csv_folder(
    sheets: dict[str, pd.DataFrame],
    folder: str | Path,
) -> list[Path]:
    """Exporta varias tablas como CSV dentro de una carpeta.

    Args:
        sheets: Diccionario {nombre_archivo: DataFrame}.
        folder: Carpeta destino.

    Returns:
        Lista de paths generados.
    """
    out_dir = Path(folder)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name, frame in sheets.items():
        safe = _safe_filename(name)
        paths.append(export_dataframe_to_csv(frame, out_dir / f"{safe}.csv"))
    return paths


def export_to_excel(
    sheets: dict[str, pd.DataFrame],
    filepath: str | Path,
) -> Path:
    """Exporta múltiples DataFrames a un libro Excel (una hoja por tabla).

    Args:
        sheets: Diccionario {nombre_hoja: DataFrame}.
        filepath: Ruta del archivo .xlsx.

    Returns:
        Path del archivo generado.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            safe_name = _safe_sheet_name(sheet_name)
            export_frame = frame.copy()
            # Excel no acepta timezone en índices datetime.
            if isinstance(export_frame.index, pd.DatetimeIndex):
                export_frame.index = export_frame.index.tz_localize(None)
            export_frame.to_excel(writer, sheet_name=safe_name)

    return path


def build_export_payload(
    prices: pd.DataFrame | None = None,
    fundamentals: pd.DataFrame | None = None,
    metrics_summary: pd.DataFrame | None = None,
    portfolios: dict[str, dict] | None = None,
    covariance: pd.DataFrame | None = None,
    correlation: pd.DataFrame | None = None,
    frontier: pd.DataFrame | None = None,
    cal: pd.DataFrame | None = None,
    extra_sheets: dict[str, pd.DataFrame] | None = None,
) -> dict[str, pd.DataFrame]:
    """Arma el diccionario de hojas para exportar el análisis completo.

    Args:
        prices: Precios históricos.
        fundamentals: Fundamentales por ticker.
        metrics_summary: Resumen de métricas por activo.
        portfolios: Salida de build_standard_portfolios.
        covariance: Matriz de covarianzas.
        correlation: Matriz de correlaciones.
        frontier: Frontera eficiente.
        cal: Capital Allocation Line.
        extra_sheets: Hojas adicionales opcionales.

    Returns:
        Diccionario listo para export_to_excel / CSV.
    """
    sheets: dict[str, pd.DataFrame] = {}

    if prices is not None:
        sheets["Precios"] = prices
    if fundamentals is not None:
        sheets["Fundamentales"] = fundamentals
    if metrics_summary is not None:
        sheets["Metricas_Activos"] = metrics_summary
    if portfolios is not None:
        sheets["Portafolios"] = portfolios_summary_table(portfolios)
        sheets["Pesos"] = _weights_table(portfolios)
    if covariance is not None:
        sheets["Covarianzas"] = covariance
    if correlation is not None:
        sheets["Correlaciones"] = correlation
    if frontier is not None:
        sheets["Frontera_Eficiente"] = frontier
    if cal is not None:
        sheets["CAL"] = cal
    if extra_sheets:
        sheets.update(extra_sheets)

    if not sheets:
        raise ValueError("No hay datos para exportar.")
    return sheets


def export_analysis_to_excel(
    filepath: str | Path,
    **payload_kwargs: Any,
) -> Path:
    """Atajo: construye el payload y lo exporta a Excel.

    Args:
        filepath: Ruta .xlsx.
        **payload_kwargs: Argumentos de build_export_payload.

    Returns:
        Path del Excel generado.
    """
    sheets = build_export_payload(**payload_kwargs)
    return export_to_excel(sheets, filepath)


def export_analysis_to_csv_folder(
    folder: str | Path,
    **payload_kwargs: Any,
) -> list[Path]:
    """Atajo: construye el payload y lo exporta como varios CSV.

    Args:
        folder: Carpeta destino.
        **payload_kwargs: Argumentos de build_export_payload.

    Returns:
        Lista de CSV generados.
    """
    sheets = build_export_payload(**payload_kwargs)
    return export_dataframes_to_csv_folder(sheets, folder)


def _weights_table(portfolios: dict[str, dict]) -> pd.DataFrame:
    """Convierte los pesos de cada portafolio en una tabla."""
    rows = []
    for name, portfolio in portfolios.items():
        row = {"Portafolio": name}
        for ticker, weight in portfolio["weights"].items():
            row[ticker] = float(weight)
        rows.append(row)
    return pd.DataFrame(rows).set_index("Portafolio")


def _safe_sheet_name(name: str) -> str:
    """Normaliza nombres de hoja para Excel (máx. 31 caracteres)."""
    cleaned = "".join(ch if ch not in r"[]:*?/\\" else "_" for ch in str(name))
    return cleaned[:31] or "Hoja"


def _safe_filename(name: str) -> str:
    """Normaliza nombres de archivo CSV."""
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(name))
    return cleaned.strip("_") or "datos"
