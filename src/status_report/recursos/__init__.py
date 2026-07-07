"""Recursos estaticos empacotados com o aplicativo (logo, imagens)."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path

LOGO_PNG = "ghr_logo.png"


def caminho_logo() -> Path | None:
    """Retorna o caminho da logo GHR (PNG) ou None se nao encontrada."""
    try:
        caminho = Path(str(files("status_report.recursos") / LOGO_PNG))
    except Exception:
        caminho = Path(__file__).with_name(LOGO_PNG)
    return caminho if caminho.exists() else None
