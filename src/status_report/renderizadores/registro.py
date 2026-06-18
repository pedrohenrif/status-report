"""Registro central dos renderizadores ativos.

Para incluir um novo slide na automacao basta:
1. criar um novo renderizador em `renderizadores/<nome>.py` que respeite
   o `RenderizadorSlide` (ver `protocolo.py`);
2. instanciar o renderizador em `RENDERIZADORES_ATIVOS` abaixo.

A ordem nao importa para a substituicao de placeholders, mas pode ser util
manter a ordem dos slides do template para clareza.
"""
from __future__ import annotations

from status_report.renderizadores.protocolo import RenderizadorSlide
from status_report.renderizadores.slide_capa import RenderizadorCapa
from status_report.renderizadores.slide_fechamento import RenderizadorFechamento


RENDERIZADORES_ATIVOS: list[RenderizadorSlide] = [
    RenderizadorCapa(),
    RenderizadorFechamento(),
]
