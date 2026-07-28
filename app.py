"""
Punto de entrada del Dashboard Financiero.

Inicializa Streamlit, el estado de sesión y la página de inicio.
El resto de pantallas vive en la carpeta pages/.
"""

import streamlit as st

import config
from modules.helpers import apply_theme
from modules.state import init_session_state


def configure_app() -> None:
    """Configura el título, icono y layout de la aplicación."""
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=config.APP_ICON,
        layout=config.PAGE_LAYOUT,
        initial_sidebar_state="expanded",
    )
    apply_theme()


def render_home() -> None:
    """Renderiza la pantalla de inicio."""
    st.title(config.APP_TITLE)
    st.markdown(
        """
        Bienvenido al **Dashboard Financiero para Optimización de Portafolios**.

        ### Cómo usarlo
        1. Ve a **Configuración** y ajusta Rf, benchmark y periodo (opcional).
        2. Ve a **Portafolio**, escribe los tickers y pulsa **Analizar**.
        3. Revisa resultados en **Dashboard** y **Optimización**.
        4. Exporta a Excel/CSV desde **Configuración** o **Dashboard**.
        """
    )

    if st.session_state.get("analysis_ready"):
        st.success(
            f"Análisis listo para: {', '.join(st.session_state.tickers)} "
            f"| Periodo: {st.session_state.period} "
            f"| Benchmark: {st.session_state.benchmark}"
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
