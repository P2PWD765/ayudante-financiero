# Documento de contexto — Dashboard Financiero / Portfolio Manager

**Proyecto:** Ayudante Financiero / Portafolio Dashboard  
**Ubicación local:** `C:\Users\pgare\OneDrive\Desktop\DESARROLLO PYTHON\AYUDANTE FINANCIERO`  
**Repositorio GitHub:** https://github.com/P2PWD765/ayudante-financiero  
**Fecha de este documento:** 28 jul 2026  
**Estado:** MVP (fases 0–7c) + **extensiones A–E** (VaR/CVaR, Monte Carlo, TradingView, Black-Litterman, grupos multi-benchmark). Cambios A–E aún **locales** (no subidos a GitHub al cerrar esta actualización).

---

## 1. Objetivo del proyecto

Desarrollar una aplicación profesional en **Python + Streamlit** para:

- Analizar acciones con datos históricos (Yahoo Finance).
- Construir y evaluar portafolios (varios **grupos** de tickers, cada uno con su benchmark).
- Optimizar Markowitz: equiponderado, máximo Sharpe, mínima varianza; frontera + CAL.
- **Black-Litterman** con views del usuario.
- Medir riesgo: VaR paramétrico / histórico / CVaR + **Monte Carlo** (3 escenarios).
- Ver gráficos **TradingView** por activo.
- Clasificar activos (sector / industria) con **FinanceDatabase** + mercado vía benchmark.
- Exportar resultados a Excel/CSV.

Prioridades de diseño:

- Arquitectura modular (UI en `pages/`, lógica en `modules/`).
- Código documentado, funciones pequeñas, sin duplicar lógica.
- UI legible: paleta azul, texto con buen contraste, cada número con contexto.

---

## 2. Stack tecnológico

| Tecnología | Uso |
|------------|-----|
| Python 3.x | Backend / lógica |
| Streamlit | Dashboard / UI |
| pandas, NumPy, SciPy | Datos y métricas |
| yfinance | Precios y fundamentales |
| financedatabase | Metadatos (sector, industria, país) |
| CVXPY | Optimización Markowitz / BL |
| Plotly | Gráficos |
| OpenPyXL | Exportación Excel |
| TradingView widget | Gráfico interactivo embebido (sin API key) |
| Git + GitHub | Control de versiones |
| VS Code / Cursor | Entorno de desarrollo |

Entorno virtual: `.venv` en la raíz (no se sube a Git).

---

## 3. Estructura del proyecto

```text
AYUDANTE FINANCIERO/
├── app.py                 # Entrada Streamlit (home) + apply_theme()
├── config.py              # Config central, paleta, MC, BL, grupos, TradingView
├── requirements.txt
├── README.md
├── CONTEXTO_PROYECTO.md   # Este documento
├── .gitignore
├── .streamlit/config.toml
├── reload.py              # Limpia caché y reinicia Streamlit
├── pages/                 # Solo interfaz (orden del menú lateral)
│   ├── 1_Dashboard.py
│   ├── 2_Optimización.py  # Markowitz + Black-Litterman
│   ├── 3_Portafolio.py    # Grupos de tickers + clasificación + analizar
│   ├── 4_Riesgo.py        # VaR/CVaR + Monte Carlo
│   └── 5_Configuracion.py
└── modules/               # Solo lógica
    ├── helpers.py
    ├── data.py
    ├── metrics.py         # Incluye VaR histórico y CVaR
    ├── portfolio.py
    ├── optimization.py
    ├── black_litterman.py
    ├── montecarlo.py
    ├── classification.py  # Mercado vía benchmark + FinanceDatabase
    ├── tradingview.py     # Embed Advanced Chart
    ├── charts.py
    ├── export.py
    └── state.py           # Grupos + pipeline + grupo activo
```

---

## 4. Flujo de la aplicación

```text
Usuario define 1–3 grupos (tickers + benchmark cada uno)
  → por grupo: descarga precios (yfinance) + benchmark
  → retornos mensuales log → métricas + 3 portafolios
  → Markowitz (frontera / CAL) + clasificación sector/industria
  → (opcional) VaR/CVaR, Monte Carlo, Black-Litterman, TradingView
  → selector de grupo activo en Dashboard / Optimización / Riesgo
  → export Excel/CSV
```

### Cómo usar (usuario)

1. **Configuración** — Rf, periodo, capital; benchmark por defecto para nuevas filas; exportar.
2. **Portafolio** — una o más filas de tickers (cada una con su benchmark) → **Analizar portafolios**.
3. **Dashboard** — métricas, VaR, fundamentales, TradingView, matrices, gráficos.
4. **Optimización** — pestaña Markowitz (frontera + CAL) y pestaña Black-Litterman.
5. **Riesgo** — VaR/CVaR + Monte Carlo (Pesimista / Normal / Optimista).

---

## 5. Decisiones de producto acordadas

### 5.1 Tres portafolios siempre (por grupo)

1. **Equiponderado** (`1/n`)  
2. **Máximo Sharpe**  
3. **Mínima varianza**  

Long-only (pesos ≥ 0).

### 5.2 Indicadores por portafolio

Rendimiento, varianza, σ, Beta, Sharpe, Treynor, Jensen (mensual/anual); matrices cov/corr; VaR paramétrico, VaR histórico, CVaR (95%).

### 5.3 Fundamentales (sin ROIC en v1)

Market Cap, Enterprise Value, EV/EBITDA, P/S, ROA, ROE (Yahoo `info`).

### 5.4 Comparación dual Calculado vs Yahoo

Cuando exista: **Beta calculado** | **Beta (Yahoo)**; si no → `N/A`.

### 5.5 Tasa libre de riesgo (Rf)

Editable en Configuración (default **4%**). Selector de tipo de tasa (T-Bill, 10Y…) → diferido.

### 5.6 Benchmark y grupos (Fase E)

- Default global / nuevas filas: `^GSPC` (S&P 500).
- Hasta **3 grupos** (`MAX_ANALYSIS_GROUPS`): cada uno con tickers + benchmark propio.
- **Regla de producto:** el benchmark del grupo **identifica el mercado**  
  (ej. `^N225` → Japón, `^GSPC` → Estados Unidos). Mapa en `BENCHMARK_MARKET_MAP`.
- Sector / industria / industry_group: **FinanceDatabase** (fallback Yahoo).
- Validador de ticker Yahoo en Portafolio.

### 5.7 Frecuencia de cálculo

- Precios **diarios**; UI y cálculos en **mensual y anual**.
- Retornos **log**: \(R = \ln(P_t / P_{t-1})\).
- Anualización: \(\mu \times 12\), \(\sigma \times \sqrt{12}\), \(\Sigma \times 12\).

### 5.8 Beta

Individual ≈ pendiente vs benchmark del **grupo** (retornos mensuales log).  
Portafolio = SUMAPRODUCTO(pesos, betas).

### 5.9 Fórmulas de riesgo (extensión A)

- VaR **paramétrico**: \(\mathrm{Capital} \times (Z\cdot\sigma - \mu)\) (positivo = pérdida).
- VaR **histórico**: \(-\)cuantil \((1-\alpha)\) de retornos.
- **CVaR**: media de la cola peor o igual al VaR histórico.
- También en **unidades de retorno** (%) y en **dinero** (× capital).

### 5.10 Monte Carlo (Fase B)

- Retornos mensuales multivariados \(N(\mu, \Sigma)\), pesos fijos, \(V_t = V_{t-1}\exp(r_p)\).
- **3 escenarios** con la misma muestra aleatoria (`MONTE_CARLO_SCENARIOS`):
  - **Pesimista:** \(\mu - 1\sigma\), vol × 1.25  
  - **Normal:** histórico  
  - **Optimista:** \(\mu + 1\sigma\), vol × 0.85  
- Página **Riesgo**: fan chart, histograma, VaR/CVaR MC.

### 5.11 Black-Litterman (Fase D)

- Prior: \(\pi = \delta \Sigma w_{mercado}\) (Market Cap si hay; si no, equiponderado).
- Views **absolutas** o **relativas** + confianza → \(\mu_{BL}\) → Máx. Sharpe BL.
- UI: Optimización → pestaña Black-Litterman (`BL_TAU`, `BL_DELTA`).

### 5.12 TradingView (Fase C)

- Widget Advanced Chart embebido (Dashboard y Portafolio).
- Mapeo Yahoo → TradingView en `TRADINGVIEW_SYMBOL_MAP` (ej. `^GSPC` → `SP:SPX`, `BRK-B` → `NYSE:BRK.B`).

### 5.13 UI — Japanese Minimalism (PGA)

Tema profesional **blanco + azul índigo + morado muted** (jul 2026).

| Token | Hex | Uso |
|-------|-----|-----|
| `background` | `#F7F6F4` | Fondo washi / off-white |
| `card` | `#FFFFFF` | Superficies |
| `text` | `#1A2744` | Índigo navy (texto) |
| `text_muted` | `#5A6F8C` | Azul acero |
| `primary` | `#2C3E6B` | Azul índigo (acciones, headers) |
| `primary_soft` | `#E4E8F0` | Soft fill / filas |
| `secondary` | `#6B5B7A` | Morado muted (acentos) |
| `secondary_soft` | `#EDE8F0` | Hover / soft purple |
| `danger` | `#8B4A4A` | Alerta contenida |
| `hairline` | `#D4D2CE` | Bordes finos (ma) |

- Tipografía: **Shippori Mincho** (títulos) + **Zen Kaku Gothic New** (cuerpo).
- Marca: `assets/pga_logo.png` · tagline **design by PGA**.
- Bordes 1px, radios 2px, sin sombras ni neón.

### 5.14 UI — indicadores legibles

`show_metric`, `INDICATOR_HELP`, captions en todas las páginas nuevas (Riesgo, BL, grupos).

---

## 6. Fases de construcción (historial)

| Fase | Contenido | Estado |
|------|-----------|--------|
| 0–6 | Scaffold → datos → métricas → portafolios → frontera/CAL → charts/export → UI | Hecha |
| 7a–7c | Paleta azul, indicadores legibles, GitHub | Hecha |
| **A** | VaR histórico + CVaR por activo y por portafolio | **Hecha** |
| **B** | Monte Carlo + 3 escenarios (página Riesgo) | **Hecha** |
| **C** | TradingView por activo seleccionado | **Hecha** |
| **D** | Black-Litterman (views + comparación Markowitz) | **Hecha** |
| **E** | Grupos multi-ticker / multi-benchmark + clasificación + validador Yahoo | **Hecha** |

**Pendiente sugerido (v1.1+):**

- Subir commits A–E a GitHub (cuando el usuario lo pida).
- Selector de tipo de Rf automático; ROIC.
- Fama-French, backtesting.
- PDF / PowerPoint en export.
- Más de 3 grupos; vista comparar grupos lado a lado.

---

## 7. Cómo ejecutar

### En VS Code / Cursor (recomendado)

1. **File → Open Folder** → carpeta del proyecto.  
2. **Terminal → New Terminal**.  
3. Activar entorno:

```powershell
cd "C:\Users\pgare\OneDrive\Desktop\DESARROLLO PYTHON\AYUDANTE FINANCIERO"
.\.venv\Scripts\Activate.ps1
```

4. Si faltan dependencias (p. ej. tras añadir `financedatabase`):

```powershell
pip install -r requirements.txt
```

5. Arrancar:

```powershell
streamlit run app.py
```

6. Abrir en el navegador: **http://localhost:8501**

Para detener: **Ctrl+C** en la terminal.

### Arranque directo (sin activar venv)

```powershell
cd "C:\Users\pgare\OneDrive\Desktop\DESARROLLO PYTHON\AYUDANTE FINANCIERO"
.\.venv\Scripts\streamlit.exe run app.py
```

### Recarga limpia (caché / versión vieja en memoria)

```powershell
.\.venv\Scripts\python.exe reload.py
```

**Nota:** cambios en `.streamlit/config.toml` requieren **reiniciar** Streamlit.

### Instalación en otra máquina (desde GitHub)

> El repo remoto puede estar **atrás** respecto a las fases A–E hasta que se haga push.

```powershell
git clone https://github.com/P2PWD765/ayudante-financiero.git
cd ayudante-financiero
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

---

## 8. Problemas encontrados y soluciones

(Resumen del MVP; sigue vigente.)

- Caché de Streamlit / módulos viejos → `importlib.reload` en `state.py` + `reload.py`.
- Matrices poco visibles → tablas + heatmaps.
- Diferencias vs Excel por precios ajustados / fin de mes.
- Tema CSS: reiniciar Streamlit tras cambiar `config.toml`.
- `delta` de `st.metric` confundía retorno → métricas separadas.
- `gh`/`git` fuera del PATH en algunas terminales Windows.

**Nuevo (A–E):**

- FinanceDatabase carga catálogo la primera vez (puede tardar unos segundos).
- TradingView necesita red en el navegador.
- Si un grupo tiene ticker inválido, ese grupo falla; los demás pueden completarse (aviso en `last_error`).

---

## 9. Configuración relevante (`config.py`)

### Datos / optimización

- `DEFAULT_PERIOD`, `DEFAULT_BENCHMARK`, `RISK_FREE_RATE`, `LONG_ONLY`, frontera/CAL.

### Monte Carlo

- `MONTE_CARLO_SIMULATIONS`, `MONTE_CARLO_HORIZON_MONTHS`, `MONTE_CARLO_SEED`, `MONTE_CARLO_SCENARIOS`.

### Black-Litterman

- `BL_TAU`, `BL_DELTA`, `BL_DEFAULT_CONFIDENCE`.

### Grupos / clasificación

- `MAX_ANALYSIS_GROUPS = 3`
- `BENCHMARK_MARKET_MAP` (benchmark → mercado/país)

### TradingView

- `TRADINGVIEW_HEIGHT`, `TRADINGVIEW_INTERVAL`, `TRADINGVIEW_THEME`, `TRADINGVIEW_SYMBOL_MAP`

### UI

- `COLORS`, `CHART_COLORWAY`, heatmaps, `APP_TITLE`

---

## 10. Módulos — responsabilidad breve

| Módulo | Responsabilidad |
|--------|-----------------|
| `data.py` | Precios, fundamentales, benchmark |
| `metrics.py` | Retornos, Beta, Sharpe, VaR paramétrico/histórico, CVaR |
| `portfolio.py` | 3 portafolios + evaluación + VaR/CVaR de portafolio |
| `optimization.py` | Min var, max Sharpe, frontera, CAL |
| `black_litterman.py` | Prior π, views, μ_BL, pesos BL |
| `montecarlo.py` | Simulación + 3 escenarios |
| `classification.py` | Mercado vía benchmark; sector/industria (FinanceDatabase) |
| `tradingview.py` | Mapeo Yahoo→TV + embed |
| `charts.py` | Plotly (incl. fan MC, escenarios) |
| `export.py` | Excel/CSV |
| `state.py` | Grupos, `run_groups_analysis`, grupo activo |
| `helpers.py` | Tema, formatos, glosario |

---

## 11. Exportación

Hojas típicas: Precios, Fundamentales, Métricas, Portafolios, Pesos, Covarianzas, Correlaciones, Frontera, CAL.  
Carpeta `exports/` (en `.gitignore`).

---

## 12. Compartir con un compañero

GitHub (cuando A–E estén pusheados) o ZIP **sin** `.venv` ni `exports/`.

```powershell
git add .
git commit -m "Describe el cambio"
git push
```

(Solo cuando el usuario lo pida explícitamente.)

---

## 13. Contexto de validación manual

Validación histórica vs Excel: acciones US, S&P 500, retornos mensuales log, Beta SUMAPRODUCTO.  
Tickers de prueba: `MSFT, GOOGL, AMZN, COST, CVX, LMT, V`  
Grupo Japón de prueba: `7203.T, 6758.T` con benchmark `^N225`.

---

## 14. Próximos pasos sugeridos

1. Push a GitHub de fases A–E (cuando se autorice).  
2. Exportar retornos mensuales 1:1 vs Excel.  
3. Rf automático / ROIC / backtesting.  
4. Comparar grupos lado a lado en una sola vista.

---

*Documento actualizado al 28 jul 2026: MVP + fases A–E (VaR/CVaR, Monte Carlo, TradingView, Black-Litterman, grupos multi-benchmark).*
