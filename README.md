# Dashboard Financiero / Portafolio

Aplicación en **Python + Streamlit** para analizar acciones, construir portafolios
y optimizarlos con Markowitz (datos históricos de Yahoo Finance).

## Características

- Descarga de precios y fundamentales (Yahoo Finance)
- 3 portafolios siempre: Equiponderado, Máximo Sharpe, Mínima varianza
- Métricas mensual/anual: rendimiento, riesgo, Beta, Sharpe, Treynor, Jensen, VaR
- Frontera eficiente + Capital Allocation Line (CAL)
- Heatmaps de correlación / covarianza
- Exportación a Excel y CSV

## Requisitos

- Python 3.10+ recomendado
- Conexión a internet (yfinance)

## Instalación

```powershell
git clone https://github.com/TU_USUARIO/ayudante-financiero.git
cd ayudante-financiero
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

En macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecución

```powershell
streamlit run app.py
```

Abre: http://localhost:8501

Recarga limpia (si hay caché vieja):

```powershell
.\.venv\Scripts\python.exe reload.py
```

## Cómo usar

1. **Configuración** — Rf, benchmark, periodo, capital
2. **Portafolio** — tickers → **Analizar portafolios**
3. **Dashboard** — métricas, matrices, gráficos
4. **Optimización** — frontera eficiente y CAL
5. Exporta desde **Configuración** o **Dashboard**

Tickers de prueba: `MSFT, GOOGL, AMZN, COST, CVX, LMT, V`

## Estructura

```text
.
├── app.py                 # Entrada Streamlit
├── config.py              # Configuración central (colores, Rf, etc.)
├── requirements.txt
├── reload.py              # Reinicio limpio de Streamlit
├── pages/                 # Solo interfaz
│   ├── 1_Dashboard.py
│   ├── 2_Portafolio.py
│   ├── 3_Optimizacion.py
│   └── 4_Configuracion.py
└── modules/               # Solo lógica
    ├── helpers.py
    ├── data.py
    ├── metrics.py
    ├── portfolio.py
    ├── optimization.py
    ├── charts.py
    ├── export.py
    └── state.py
```

## Notas

- **No** subas la carpeta `.venv` (cada quien crea la suya).
- Las exportaciones se guardan en `exports/` (ignorada por git).
- Detalle de diseño y fórmulas: ver `CONTEXTO_PROYECTO.md`.

## Licencia

Uso educativo / personal. Ajusta la licencia si publicas el repo.
