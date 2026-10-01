"""
Punto de entrada del Dashboard Financiero (PGA).

Inicializa Streamlit, el estado de sesión y la página de inicio.
El resto de pantallas vive en la carpeta pages/.
"""

from pathlib import Path

import streamlit as st

import config
from modules.helpers import apply_theme
from modules.state import init_session_state

_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "pga_logo.png"


def configure_app() -> None:
    """Configura el título, icono y layout de la aplicación."""
    icon = str(_LOGO_PATH) if _LOGO_PATH.exists() else config.APP_BRAND
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=icon,
        layout=config.PAGE_LAYOUT,
        initial_sidebar_state="expanded",
    )
    apply_theme()


def render_home() -> None:
    """Renderiza la pantalla de inicio con branding PGA."""
    col_logo, col_copy = st.columns([1, 2], gap="large")
    with col_logo:
        if _LOGO_PATH.exists():
            st.image(str(_LOGO_PATH), use_container_width=True)
        else:
            st.markdown(
                f"""
                <div class="pga-hero">
                    <h1>{config.APP_BRAND}</h1>
                    <hr class="pga-line" />
                    <p class="pga-sub">{config.APP_TAGLINE}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with col_copy:
        st.markdown(
            f"""
            <div class="pga-hero">
                <h1>{config.APP_BRAND}</h1>
                <hr class="pga-line" />
                <p class="pga-sub">{config.APP_TAGLINE}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            Análisis y optimización de portafolios con una interfaz
            contenida: Markowitz, Black-Litterman, riesgo (VaR / Monte Carlo)
            y grupos multi-benchmark.
            """
        )

    st.markdown("##### Cómo usarlo")
    st.markdown(
        """
        1. **Configuración** — Rf, periodo y capital.  
        2. **Portafolio** — filas de tickers + benchmark → **Analizar**.  
        3. **Dashboard**, **Optimización** y **Riesgo** — resultados del grupo activo.  
        4. Exportar desde **Configuración**.
        """
    )

    if st.session_state.get("analysis_ready"):
        group_name = st.session_state.get("active_group_name") or "—"
        st.success(
            f"Análisis listo · Grupo: {group_name} · "
            f"Activos: {', '.join(st.session_state.tickers)} · "
            f"Periodo: {st.session_state.period} · "
            f"Benchmark: {st.session_state.benchmark}"
        )
    else:
        st.info("Aún no hay análisis. Empieza en la página **Portafolio**.")


def main() -> None:
    """Arranca la aplicación Streamlit."""
    configure_app()
    init_session_state()
    render_home()


if __name__ == "__main__":
    main()
