"""
Configuración central del Dashboard Financiero.

Toda configuración general del proyecto debe vivir aquí
para evitar valores mágicos repartidos en el código.
"""

# --- Datos ---
DEFAULT_PERIOD = "5y"
DEFAULT_BENCHMARK = "^GSPC"
DEFAULT_INTERVAL = "1d"  # diario
RISK_FREE_RATE = 0.04  # tasa anual (4%)

# --- Volatilidad ---
# Si True, la volatilidad semanal/mensual se muestra anualizada.
ANNUALIZE_VOLATILITY = True
TRADING_DAYS_PER_YEAR = 252
WEEKS_PER_YEAR = 52
MONTHS_PER_YEAR = 12

# --- Fundamentales a solicitar (sin ROIC en v1) ---
FUNDAMENTAL_FIELDS = {
    "marketCap": "Market Cap",
    "enterpriseValue": "Enterprise Value",
    "enterpriseToEbitda": "EV/EBITDA",
    "priceToSalesTrailing12Months": "P/S",
    "returnOnAssets": "ROA",
    "returnOnEquity": "ROE",
}

# --- Comparación dual (regla de producto) ---
# En Dashboard / tablas / exportación siempre mostrar, cuando exista:
# 1) Valor calculado por el programa (nuestras fórmulas).
# 2) Valor de referencia publicado por Yahoo Finance.
# Si Yahoo no publica ese indicador, mostrar "N/A" en la columna Yahoo.
SHOW_YAHOO_COMPARISON = True

# Campos de Yahoo útiles como referencia frente a métricas calculadas.
YAHOO_REFERENCE_FIELDS = {
    "beta": "Beta (Yahoo)",
}

# --- Optimización ---
LONG_ONLY = True
EFFICIENT_FRONTIER_POINTS = 40
CAL_POINTS = 25
# Extiende la CAL más allá del tangency (1.0 = hasta el max Sharpe).
CAL_MAX_RISKY_WEIGHT = 1.5

# --- UI / tema ---
# Paleta "Azul Dashboard" — claro, legible, azul como color principal.
# Sin morados ni tonos neón: contraste alto texto/fondo.
APP_TITLE = "Dashboard Financiero"
APP_ICON = "📈"
PAGE_LAYOUT = "wide"

COLORS = {
    "background": "#F1F5F9",   # Gris azulado suave (fondo)
    "card": "#FFFFFF",         # Blanco (tarjetas / tablas)
    "text": "#0F172A",         # Slate casi negro (texto principal)
    "text_muted": "#334155",   # Slate medio (captions / ejes secundarios)
    "primary": "#1D4ED8",      # Azul principal (barras, líneas A, headers)
    "primary_soft": "#DBEAFE", # Azul muy suave (filas alternas / highlights)
    "secondary": "#0369A1",    # Azul cielo oscuro (líneas B / series 2)
    "danger": "#B91C1C",       # Rojo mate (alertas / mínima varianza)
    "neutral": "#64748B",      # Gris slate (marcadores neutros)
    "on_primary": "#FFFFFF",   # Texto sobre fondos azul oscuro
}

# Series múltiples: azules / slate / teal (sin púrpuras ni neón).
CHART_COLORWAY = [
    COLORS["primary"],   # #1D4ED8
    COLORS["secondary"], # #0369A1
    "#0F766E",           # teal oscuro
    "#1E3A8A",           # navy
    "#475569",           # slate
    "#0284C7",           # sky
    COLORS["danger"],    # alerta
]

# Escalas de heatmaps (legibles con texto oscuro).
# Correlación: rojo (negativa) ↔ verde (positiva).
HEATMAP_CORR = [
    [0.0, "#DC2626"],  # correlación negativa
    [0.25, "#FECACA"],
    [0.5, "#FFFFFF"],  # cero / neutro
    [0.75, "#BBF7D0"],
    [1.0, "#16A34A"],  # correlación positiva
]
HEATMAP_COV = [
    [0.0, "#EFF6FF"],
    [0.5, "#93C5FD"],
    [1.0, "#2563EB"],
]
