# Documento de contexto — Dashboard Financiero / Portfolio Manager

**Proyecto:** Ayudante Financiero / Portafolio Dashboard  
**Ubicación local:** `C:\Users\pgare\OneDrive\Desktop\DESARROLLO PYTHON\AYUDANTE FINANCIERO`  
**Repositorio GitHub:** https://github.com/P2PWD765/ayudante-financiero  
**Fecha de este documento:** 28 jul 2026  
**Estado:** MVP funcional (fases 0–6) + UI/tema azul + indicadores legibles + repo en GitHub

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
- UI legible: paleta coherente, texto con buen contraste, cada número con contexto.

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
| Git + GitHub | Control de versiones y colaboración |
| VS Code / Cursor | Entorno de desarrollo |

Entorno virtual: `.venv` en la raíz del proyecto (no se sube a Git).

---

## 3. Estructura del proyecto

```text
AYUDANTE FINANCIERO/
├── app.py                 # Entrada Streamlit (home) + apply_theme()
├── config.py              # Configuración central + paleta de colores
├── requirements.txt
├── README.md
├── CONTEXTO_PROYECTO.md   # Este documento
├── .gitignore             # Excluye .venv, exports, cachés, secretos
├── .streamlit/
│   └── config.toml        # Tema Streamlit (colores base)
├── reload.py              # Limpia caché y reinicia Streamlit
├── pages/                 # Solo interfaz
│   ├── 1_Dashboard.py
│   ├── 2_Portafolio.py
│   ├── 3_Optimizacion.py
│   └── 4_Configuracion.py
└── modules/               # Solo lógica
    ├── helpers.py         # Formatos, tema CSS, tablas, show_metric, glosario
    ├── data.py
    ├── metrics.py
    ├── portfolio.py
    ├── optimization.py
    ├── charts.py          # Plotly + paleta unificada
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
  → gráficos en Streamlit (paleta azul)
  → export Excel/CSV
```

### Cómo usar (usuario)

1. **Configuración** — Rf, benchmark, periodo, capital; exportar.
2. **Portafolio** — tickers → **Analizar portafolios**.
3. **Dashboard** — métricas, fundamentales, matrices, gráficos.
4. **Optimización** — frontera eficiente + CAL (riesgo y retorno en métricas separadas).

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

### 5.10 UI — paleta "Azul Dashboard" (jul 2026)

Decisión: interfaz clara, **azul como color principal**, sin morados ni tonos neón. Texto oscuro legible sobre fondos claros.

| Token | Hex | Uso |
|-------|-----|-----|
| `background` | `#F1F5F9` | Fondo general |
| `card` | `#FFFFFF` | Tarjetas, tablas, paneles Plotly |
| `text` | `#0F172A` | Texto principal y ejes |
| `text_muted` | `#334155` | Captions, labels secundarios |
| `primary` | `#1D4ED8` | Barras, líneas A, headers de tabla |
| `primary_soft` | `#DBEAFE` | Filas alternas en tablas |
| `secondary` | `#0369A1` | Líneas B, segunda serie |
| `danger` | `#B91C1C` | Alertas, mínima varianza en gráficos |
| `neutral` | `#64748B` | Marcadores neutros |
| `on_primary` | `#FFFFFF` | Texto sobre fondo azul oscuro |

**Heatmaps:**

- **Correlación:** escala rojo → blanco → verde (`HEATMAP_CORR` en `config.py`).
- **Covarianza:** escala azul (`HEATMAP_COV`).

**Implementación:**

- `config.py` — `COLORS`, `CHART_COLORWAY`, `HEATMAP_CORR`, `HEATMAP_COV`
- `.streamlit/config.toml` — tema base Streamlit
- `modules/helpers.py` — `apply_theme()` inyecta CSS en todas las páginas
- `modules/charts.py` — `_style_figure()` aplica paleta a todos los gráficos Plotly
- `modules/helpers.py` — `theme_styler()` estiliza tablas (header azul, texto oscuro)

Todas las páginas llaman `apply_theme()` justo después de `st.set_page_config()`.

### 5.11 UI — indicadores legibles para el usuario (jul 2026)

Regla: **cada número visible debe indicar qué representa** (etiqueta, caption o tooltip).

Implementado en `modules/helpers.py`:

| Función / constante | Rol |
|---------------------|-----|
| `INDICATOR_HELP` | Glosario de tooltips (Rf, riesgo σ, retorno, Sharpe, Beta, etc.) |
| `show_metric()` | `st.metric` con `help=` y etiquetas claras |
| `format_labeled()` | Valor + etiqueta corta (ej. `13.33% · retorno`) |
| `theme_styler()` | Tablas con headers y contraste coherentes |

**Cambio importante en Optimización:** riesgo y retorno van en **métricas separadas** (antes el retorno aparecía como `delta` de Streamlit y parecía un “aumento” del riesgo).

**Dashboard:** expander **“¿Qué significa cada indicador?”** con el glosario completo.

Captions bajo tablas, matrices y gráficos explican ejes y unidades.

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
| 7a | Paleta azul unificada (UI + tablas + gráficos + heatmaps) | Hecha |
| 7b | Indicadores legibles (`show_metric`, glosario, captions) | Hecha |
| 7c | `.gitignore`, README, repo GitHub público | Hecha |

**Pendiente sugerido (Fase 7 restante / v1.1):**

- Polish adicional de errores y docs.
- Selector de tipo de Rf + descarga automática.
- ROIC.
- Monte Carlo, Fama-French, backtesting (post-MVP).
- PDF / PowerPoint en export.

---

## 7. Cómo ejecutar

### En VS Code (recomendado)

1. **File → Open Folder** → carpeta del proyecto.
2. **Terminal → New Terminal** (`Ctrl+Ñ`).
3. Activar entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

4. Primera vez (o máquina nueva):

```powershell
pip install -r requirements.txt
```

5. Arrancar:

```powershell
streamlit run app.py
```

6. Abrir: `http://localhost:8501`

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

Hace:

1. Intenta cerrar Streamlit anterior.
2. Borra `__pycache__` / `.pyc`.
3. Arranca `streamlit run app.py`.

Si `reload.py` se traba: **Ctrl+C** y usar el arranque normal.

**Nota tema:** cambios en `.streamlit/config.toml` requieren **reiniciar** Streamlit (no basta con Rerun).

### Instalación en otra máquina (desde GitHub)

```powershell
git clone https://github.com/P2PWD765/ayudante-financiero.git
cd ayudante-financiero
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
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

### 8.5 Paleta / tema no se veía actualizado

- **Causa:** fondo nuevo muy similar al anterior; Streamlit cachea tema hasta reiniciar.
- **Mitigación:** `apply_theme()` con CSS en todas las páginas; reiniciar Streamlit tras cambios en `.streamlit/config.toml`.

### 8.6 `delta` de `st.metric` confundía al usuario

- En Optimización, el retorno esperado (ej. 13.33%) aparecía como flecha verde bajo el riesgo.
- **Solución:** métricas separadas — “Riesgo anual (σ)” y “Retorno esperado” con `show_metric()` y tooltips.

### 8.7 GitHub CLI (`gh`) no reconocido en PowerShell

- **Causa:** `gh` y `git` instalados pero fuera del `PATH` de la terminal.
- **Solución:** usar ruta completa o añadir al PATH de la sesión:

```powershell
$env:Path += ";C:\Program Files\Git\bin;C:\Program Files\GitHub CLI"
```

- Repo publicado: https://github.com/P2PWD765/ayudante-financiero (rama `main`).

---

## 9. Configuración relevante (`config.py`)

### Datos y optimización

- `DEFAULT_PERIOD = "5y"`
- `DEFAULT_BENCHMARK = "^GSPC"`
- `RISK_FREE_RATE = 0.04`
- `MONTHS_PER_YEAR = 12`
- `LONG_ONLY = True`
- `EFFICIENT_FRONTIER_POINTS`, `CAL_POINTS`, `CAL_MAX_RISKY_WEIGHT`
- `FUNDAMENTAL_FIELDS` (claves exactas Yahoo)
- `SHOW_YAHOO_COMPARISON = True`

### UI / tema

- `COLORS` — paleta Azul Dashboard (ver §5.10)
- `CHART_COLORWAY` — series múltiples en gráficos de líneas
- `HEATMAP_CORR` — correlación: rojo ↔ verde
- `HEATMAP_COV` — covarianza: escala azul
- `APP_TITLE`, `APP_ICON`, `PAGE_LAYOUT`

---

## 10. Módulos — responsabilidad breve

| Módulo | Responsabilidad |
|--------|-----------------|
| `data.py` | Descargar/limpiar precios; fundamentales; benchmark |
| `metrics.py` | Retornos log, riesgo, Beta, Sharpe, VaR, Treynor, Jensen, resumen |
| `portfolio.py` | 3 portafolios, pesos, evaluación mensual/anual, matrices |
| `optimization.py` | Min var, max Sharpe, frontera, CAL |
| `charts.py` | Plotly con `_style_figure()`; heatmaps, frontera, CAL, precios |
| `export.py` | Excel multi-hoja y CSV |
| `state.py` | `session_state` + `run_full_analysis` |
| `helpers.py` | Tickers, formatos, `apply_theme`, `theme_styler`, `show_metric`, `INDICATOR_HELP` |

---

## 11. Exportación

Hojas típicas Excel:

- Precios, Fundamentales, Métricas activos  
- Portafolios, Pesos  
- Covarianzas, Correlaciones  
- Frontera eficiente, CAL  

Ruta habitual: carpeta `exports/` (ignorada por git en `.gitignore`).

---

## 12. Compartir con un compañero

**Opción recomendada — GitHub:**

```powershell
git clone https://github.com/P2PWD765/ayudante-financiero.git
cd ayudante-financiero
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

**Alternativa:** ZIP del proyecto **sin** `.venv` ni `exports/`.

### Actualizar el repo tras cambios locales

```powershell
git add .
git commit -m "Describe el cambio"
git push
```

---

## 13. Contexto de validación manual (usuario)

El usuario validó contra Excel con acciones US, pesos iguales, S&P 500, retornos mensuales log, Beta con `PENDIENTE` y portafolio con `SUMAPRODUCTO`. Rf de referencia en su hoja: TBond 10Y ~4.55% (el default del programa es 4%, editable en Configuración).

Tickers de prueba frecuentes:

`MSFT, GOOGL, AMZN, COST, CVX, LMT, V`

---

## 14. Próximos pasos sugeridos

1. Fase 7 restante: mensajes de error más claros, prueba end-to-end documentada.  
2. Exportar serie de retornos mensuales para cruce 1:1 con Excel.  
3. v1.1: tipo de Rf automático; ROIC; más fuentes de datos.  
4. ~~Subir a GitHub para colaboración~~ → **Hecho:** https://github.com/P2PWD765/ayudante-financiero

---

*Este documento resume el acuerdo de diseño y el estado del código al 28 jul 2026 (MVP + UI azul + indicadores + GitHub).*
