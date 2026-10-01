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

# --- Monte Carlo ---
MONTE_CARLO_SIMULATIONS = 5_000
MONTE_CARLO_HORIZON_MONTHS = 12
MONTE_CARLO_SEED = 42
MONTE_CARLO_SAMPLE_PATHS = 40  # trayectorias individuales a dibujar
# Escenarios: μ' = μ + k·σ_i ; Σ' = Σ · vol_scale²
MONTE_CARLO_SCENARIOS = {
    "Pesimista": {"mu_shift_sigma": -1.0, "vol_scale": 1.25},
    "Normal": {"mu_shift_sigma": 0.0, "vol_scale": 1.0},
    "Optimista": {"mu_shift_sigma": 1.0, "vol_scale": 0.85},
}

# --- Black-Litterman ---
BL_TAU = 0.05  # incertidumbre del prior (τ)
BL_DELTA = 2.5  # aversión al riesgo para π = δ Σ w
BL_DEFAULT_CONFIDENCE = 0.50  # 0–1; más alto = la view pesa más

# --- Grupos de análisis (Fase E) ---
MAX_ANALYSIS_GROUPS = 3
# El benchmark del grupo identifica el mercado/país (regla de producto).
BENCHMARK_MARKET_MAP = {
    "^GSPC": "Estados Unidos",
    "^DJI": "Estados Unidos",
    "^IXIC": "Estados Unidos",
    "^RUT": "Estados Unidos",
    "^N225": "Japón",
    "^FTSE": "Reino Unido",
    "^GDAXI": "Alemania",
    "^IBEX": "España",
    "^FCHI": "Francia",
    "^MXX": "México",
    "^BVSP": "Brasil",
    "^HSI": "Hong Kong",
    "000001.SS": "China",
}

# --- TradingView ---
TRADINGVIEW_HEIGHT = 780
TRADINGVIEW_INTERVAL = "D"
TRADINGVIEW_THEME = "light"
# Mapa Yahoo Finance → símbolo TradingView (índices y casos especiales).
TRADINGVIEW_SYMBOL_MAP = {
    "^GSPC": "SP:SPX",
    "^DJI": "DJ:DJI",
    "^IXIC": "NASDAQ:IXIC",
    "^RUT": "TVC:RUT",
    "^VIX": "CBOE:VIX",
    "^N225": "TSE:NI225",
    "^FTSE": "TVC:UKX",
    "^GDAXI": "XETR:DAX",
    "^IBEX": "BME:IBC",
    "^FCHI": "EURONEXT:CAC40",
    "^MXX": "BMV:ME",
    "BRK-B": "NYSE:BRK.B",
    "BRK-A": "NYSE:BRK.A",
}

# --- UI / tema — Japanese Minimalism (PGA) ---
# Paleta profesional: blanco + azul índigo + morado muted.
# Espacio negativo (ma), tipografía sobria, sin neón ni kawaii.
APP_TITLE = "PGA · Dashboard Financiero"
APP_BRAND = "PGA"
APP_TAGLINE = "PGA SOFTWARE"
APP_ICON = "assets/pga_logo.png"
PAGE_LAYOUT = "wide"

COLORS = {
    # Blancos
    "background": "#F7F6F4",   # washi / off-white cálido-neutro
    "card": "#FFFFFF",         # blanco puro (superficies)
    "surface": "#EEEEEC",      # shade blanco (separadores suaves)
    # Azules
    "text": "#1A2744",         # índigo casi navy (texto)
    "text_muted": "#5A6F8C",   # azul acero muted
    "primary": "#2C3E6B",      # azul índigo principal
    "primary_soft": "#E4E8F0", # azul muy suave (filas / soft fill)
    # Morados
    "secondary": "#6B5B7A",    # morado muted profesional
    "secondary_soft": "#EDE8F0",  # lilac-gris muy suave
    # Utilidad
    "danger": "#8B4A4A",       # rojo terroso contenido (alertas)
    "neutral": "#7A7A78",      # gris piedra
    "on_primary": "#FFFFFF",   # texto sobre azul/morado oscuro
    "hairline": "#D4D2CE",     # líneas finas (ma / bordes)
}

# Series de gráficos: azul → morado → shades (sin neón).
CHART_COLORWAY = [
    COLORS["primary"],      # #2C3E6B
    COLORS["secondary"],    # #6B5B7A
    "#5A6F8C",              # acero
    "#4A3F5C",              # morado profundo
    "#1A2744",              # navy
    "#8A7A94",              # morado claro
    COLORS["danger"],       # alerta
]

# Heatmaps sobrios (sin saturación alta).
HEATMAP_CORR = [
    [0.0, "#8B4A4A"],
    [0.25, "#E8D5D5"],
    [0.5, "#FFFFFF"],
    [0.75, "#D5DCE8"],
    [1.0, "#2C3E6B"],
]
HEATMAP_COV = [
    [0.0, "#F7F6F4"],
    [0.5, "#C8D0DE"],
    [1.0, "#2C3E6B"],
]
