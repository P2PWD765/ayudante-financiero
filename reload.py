"""
Recarga limpia de la app Streamlit.

Uso:
    .\\.venv\\Scripts\\python.exe reload.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def log(msg: str) -> None:
    print(f"[reload] {msg}", flush=True)


def clear_caches() -> None:
    removed = 0
    for folder in ROOT.rglob("__pycache__"):
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
            removed += 1
    for pyc in ROOT.rglob("*.pyc"):
        try:
            pyc.unlink(missing_ok=True)
            removed += 1
        except OSError:
            pass
    cache_dir = ROOT / ".streamlit" / "cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
        removed += 1
    log(f"Cachés limpiadas ({removed}).")


def stop_streamlit_quick() -> None:
    """Intento rápido de cerrar Streamlit; no se cuelga si falla."""
    if os.name != "nt":
        return
    try:
        # taskkill es más simple/rápido que un script PowerShell largo
        subprocess.run(
            ["taskkill", "/F", "/IM", "streamlit.exe"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        log("Se intentó cerrar streamlit.exe (si existía).")
    except Exception as exc:  # noqa: BLE001
        log(f"No se pudo cerrar Streamlit automáticamente: {exc}")
        log("Si sigue abierto, cierra esa terminal con Ctrl+C.")


def start_app() -> None:
    streamlit = ROOT / ".venv" / "Scripts" / "streamlit.exe"
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    app = ROOT / "app.py"

    if not app.exists():
        raise FileNotFoundError(f"No está app.py en {ROOT}")

    os.chdir(ROOT)

    if streamlit.exists():
        cmd = [str(streamlit), "run", str(app)]
    elif python.exists():
        cmd = [str(python), "-m", "streamlit", "run", str(app)]
    else:
        cmd = [sys.executable, "-m", "streamlit", "run", str(app)]

    log("Arrancando Streamlit...")
    log("Comando: " + " ".join(cmd))
    log("Abre http://localhost:8501 si no se abre solo.")
    # No usamos execv (a veces se cuelga en Windows/OneDrive).
    raise SystemExit(subprocess.call(cmd))


def main() -> None:
    log(f"Proyecto: {ROOT}")
    stop_streamlit_quick()
    time.sleep(0.5)
    clear_caches()
    start_app()


if __name__ == "__main__":
    main()
