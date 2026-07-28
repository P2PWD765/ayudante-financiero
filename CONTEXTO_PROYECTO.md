# Documento de contexto — Dashboard Financiero / Portfolio Manager

**Proyecto:** Ayudante Financiero / Portafolio Dashboard  
**Ubicación:** `C:\Users\pgare\OneDrive\Desktop\DESARROLLO PYTHON\AYUDANTE FINANCIERO`  
**Fecha de este documento:** 27 jul 2026  
**Estado:** MVP funcional (fases 0–6) + ajustes de convención mensual/anual

---

## 1. Objetivo del proyecto

Desarrollar una aplicación profesional en **Python + Streamlit** para:

- Analizar acciones con datos históricos de internet (Yahoo Finance).
- Construir y evaluar portafolios.
- Optimizar (Markowitz): equiponderado, máximo Sharpe, mínima varianza.
- Mostrar frontera eficiente y Capital Allocation Line (CAL).
- Exportar resultados a Excel/CSV.

Prioridades de diseño:

- Arquitectura modular (fácil de mantener y ampliar).
- Separar UI (`pages/`) de lógica (`modules/`).
- Código documentado, funciones pequeñas, sin duplicar lógica.

---

## 2. Stack tecnológico

| Tecnología | Uso |
|------------|-----|
| Python 3.x | Backend / lógica |
| Streamlit | Dashboard / UI |
| pandas, NumPy, SciPy | Datos y métricas |
| yfinance | Precios y fundamentales |
| CVXPY | Optimización Markowitz |
| Plotly | Gráficos |
| OpenPyXL | Exportación Excel |
| VS Code / Cursor | Entorno de desarrollo |

Entorno virtual: `.venv` en la raíz del proyecto.

---

## 3. Estructura del proyecto

```text
AYUDANTE FINANCIERO/
├── app.py                 # Entrada Streamlit (home)
├── config.py              # Configuración central
├── requirements.txt
├── README.md
├── reload.py              # Limpia caché y reinicia Streamlit
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
    └── state.py           # session_state + pipeline de análisis
```

**Nota:** Existió una carpeta vacía `Portafolio_Dashboard/`; el código vive en la raíz `AYUDANTE FINANCIERO`.

---

## 4. Flujo de la aplicación

```text
Usuario elige tickers
  → descarga precios diarios (yfinance)
  → convierte a retornos mensuales log
  → métricas mensual + anual
  → 3 portafolios siempre
  → optimización / frontera / CAL
  → gráficos en Streamlit
  → export Excel/CSV
```

### Cómo usar (usuario)

1. **Configuración** — Rf, benchmark, periodo, capital; exportar.
2. **Portafolio** — tickers → **Analizar portafolios**.
3. **Dashboard** — métricas, fundamentales, matrices, gráficos.
4. **Optimización** — frontera eficiente + CAL.

---

## 5. Decisiones de producto acordadas

### 5.1 Tres portafolios siempre

Con cualquier set de tickers el programa genera:

1. **Equiponderado** (`1/n`)
2. **Máximo Sharpe**
3. **Mínima varianza**

Long-only (pesos ≥ 0) en v1.

### 5.2 Indicadores por portafolio

- Rendimiento (mensual y anual)
- Varianza (mensual y anual)
- Desviación estándar / riesgo (mensual y anual)
- Beta
- Sharpe
- Treynor
- Jensen (Alpha)

Además:

- Matriz de **covarianzas** (mensual)
- Matriz de **correlaciones** + **heatmap**

### 5.3 Fundamentales (v1, sin ROIC)

Desde Yahoo `info`:

- Market Cap  
- Enterprise Value  
- EV/EBITDA  
- P/S  
- ROA  
- ROE  

**ROIC:** fuera de v1 (se puede agregar después).

### 5.4 Comparación dual Calculado vs Yahoo

Regla de producto: cuando exista dato Yahoo, mostrar ambos.

Ejemplo: **Beta calculado** | **Beta (Yahoo)**.  
Si Yahoo no publica el indicador → `N/A`.

Config: `SHOW_YAHOO_COMPARISON`, `YAHOO_REFERENCE_FIELDS` en `config.py`.

### 5.5 Tasa libre de riesgo (Rf)

- v1: valor numérico editable (default **4%** en `config.py`).
- UI en Configuración permite cambiarla.
- **No** se implementó aún selector de tipo de tasa (T-Bill 3M, 10Y, etc.) → diferido a **v1.1**.

### 5.6 Benchmark

Default: `^GSPC` (S&P 500).

### 5.7 Frecuencia de cálculo (decisión clave)

- Se **descargan precios diarios**.
- Los **cálculos y la UI** trabajan en **mensual y anual** (no se muestran métricas diarias).
- Retornos: **logarítmicos**  
  \(R = \ln(P_t / P_{t-1})\)
- Anualización desde mensual:  
  - \(\mu_{anual} = \mu_{mensual} \times 12\)  
  - \(\sigma_{anual} = \sigma_{mensual} \times \sqrt{12}\)  
  - \(\Sigma_{anual} = \Sigma_{mensual} \times 12\)

### 5.8 Beta (alineado a Excel del usuario)

- Betas individuales ≈ `PENDIENTE` vs S&P (retornos mensuales log).
- Beta del portafolio = **SUMAPRODUCTO(pesos, betas)**  
  (equivalente a \(\mathrm{Cov}(R_p, R_m)/\mathrm{Var}(R_m)\)).

### 5.9 Fórmulas de métricas (documento del usuario)

Implementadas según el prompt de fórmulas:

- Rendimientos log diarios/mensuales (uso operativo: mensual).
- Acumulado: \(\exp(\sum r_i) - 1\)
- Varianza / desv. **muestral** (\(n-1\)), no poblacional.
- VaR **paramétrico**: \(\mathrm{Capital} \times (Z\cdot\sigma - \mu)\)
- Sharpe: \((R_p - R_f)/\sigma_p\)
- Alpha Jensen: \(R_p - [R_f + \beta(R_m - R_f)]\)
- Treynor: \((R_p - R_f)/\beta\)

---

## 6. Fases de construcción (historial)

| Fase | Contenido | Estado |
|------|-----------|--------|
| 0 | Scaffold: `app`, `config`, `requirements`, `helpers`, pages stub | Hecha |
| 1 | `data.py` — precios + fundamentales | Hecha |
| 2 | `metrics.py` — métricas (luego ajustada a fórmulas log / VaR paramétrico) | Hecha |
| 3 | `portfolio.py` + inicio `optimization.py` — 3 portafolios + indicadores | Hecha |
| 4 | Frontera eficiente + CAL + charts | Hecha |
| 5 | `charts.py` completo + `export.py` Excel/CSV | Hecha |
| 6 | UI Streamlit conectada (`state.py` + pages) | Hecha |
| Extra | Solo mensual/anual; matrices visibles; `reload.py`; compat caché | Hecha |

**Pendiente sugerido (Fase 7 / v1.1):**

- Polish de errores y docs.
- Selector de tipo de Rf + descarga automática.
- ROIC.
- Monte Carlo, Fama-French, backtesting (post-MVP).
- PDF / PowerPoint en export.

---

## 7. Cómo ejecutar

### Arranque normal

```powershell
cd "C:\Users\pgare\OneDrive\Desktop\DESARROLLO PYTHON\AYUDANTE FINANCIERO"
.\.venv\Scripts\streamlit.exe run app.py
```

Abrir: `http://localhost:8501`

### Recarga limpia (caché / versión vieja en memoria)

```powershell
.\.venv\Scripts\python.exe reload.py
```

Hace:

1. Intenta cerrar Streamlit anterior.
2. Borra `__pycache__` / `.pyc`.
3. Arranca `streamlit run app.py`.

Si `reload.py` se traba: **Ctrl+C** y usar el arranque normal.

### Instalación en otra máquina

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\.venv\Scripts\streamlit.exe run app.py
```

**No compartir** la carpeta `.venv` (cada quien la crea).

---

## 8. Problemas encontrados y soluciones

### 8.1 Error `expected_returns_annual`

- **Causa:** Streamlit tenía en memoria una versión vieja de `evaluate_portfolio`.
- **Mitigación:**
  - `evaluate_portfolio(..., **kwargs)` compatible.
  - `build_standard_portfolios` pasa nombres compatibles (`expected_returns`, etc.).
  - `state.py` hace `importlib.reload` de módulos de negocio al analizar.
  - Script `reload.py` para reinicio limpio.

### 8.2 Matrices covarianza / correlación “no cargaban”

- Estaban calculadas pero poco visibles.
- Se añadieron tablas + heatmaps en **Portafolio** y **Dashboard**.
- Covarianza mostrada en frecuencia **mensual** (como Excel del usuario).

### 8.3 Rendimientos vs Excel (ambos con LN)

Aunque ambos usen \(\ln(P_t/P_{t-1})\), \(\mu\) puede diferir por:

- Precios **ajustados** Yahoo vs Close sin ajustar en Excel.
- Periodo / cantidad de meses distinta.
- Criterio de “fin de mes” distinto.

Beta/corr suelen acercarse más; el rendimiento medio es más sensible a la serie exacta de precios.

### 8.4 Beta Yahoo vs calculado

- Yahoo publica beta ~5y mensual (aprox.).
- Programa: beta mensual log + SUMAPRODUCTO para portafolio.
- Diferencias pequeñas (~0.85 vs ~0.86) son normales.

---

## 9. Configuración relevante (`config.py`)

- `DEFAULT_PERIOD = "5y"`
- `DEFAULT_BENCHMARK = "^GSPC"`
- `RISK_FREE_RATE = 0.04`
- `MONTHS_PER_YEAR = 12`
- `LONG_ONLY = True`
- `EFFICIENT_FRONTIER_POINTS`, `CAL_POINTS`, `CAL_MAX_RISKY_WEIGHT`
- `FUNDAMENTAL_FIELDS` (claves exactas Yahoo)
- `SHOW_YAHOO_COMPARISON = True`

---

## 10. Módulos — responsabilidad breve

| Módulo | Responsabilidad |
|--------|-----------------|
| `data.py` | Descargar/limpiar precios; fundamentales; benchmark |
| `metrics.py` | Retornos log, riesgo, Beta, Sharpe, VaR, Treynor, Jensen, resumen |
| `portfolio.py` | 3 portafolios, pesos, evaluación mensual/anual, matrices |
| `optimization.py` | Min var, max Sharpe, frontera, CAL |
| `charts.py` | Plotly (precios, heatmaps, frontera, CAL, etc.) |
| `export.py` | Excel multi-hoja y CSV |
| `state.py` | `session_state` + `run_full_analysis` |
| `helpers.py` | Tickers, formatos, validaciones |

---

## 11. Exportación

Hojas típicas Excel:

- Precios, Fundamentales, Métricas activos  
- Portafolios, Pesos  
- Covarianzas, Correlaciones  
- Frontera eficiente, CAL  

Ruta habitual: carpeta `exports/`.

---

## 12. Compartir con un compañero

1. ZIP del proyecto **sin** `.venv`, o  
2. Repo GitHub sin `.venv`.  
3. Él crea venv + `pip install -r requirements.txt` + `streamlit run app.py`.

---

## 13. Contexto de validación manual (usuario)

El usuario validó contra Excel con acciones US, pesos iguales, S&P 500, retornos mensuales log, Beta con `PENDIENTE` y portafolio con `SUMAPRODUCTO`. Rf de referencia en su hoja: TBond 10Y ~4.55% (el default del programa es 4%, editable en Configuración).

Tickers de prueba frecuentes:

`MSFT, GOOGL, AMZN, COST, CVX, LMT, V`

---

## 14. Próximos pasos sugeridos

1. Fase 7: polish UI, mensajes de error, README de uso final.  
2. Exportar serie de retornos mensuales para cruce 1:1 con Excel.  
3. v1.1: tipo de Rf automático; ROIC; más fuentes de datos.  
4. Subir a GitHub para colaboración.

---

*Este documento resume el acuerdo de diseño y el estado del código al cierre de la conversación de construcción del MVP.*
