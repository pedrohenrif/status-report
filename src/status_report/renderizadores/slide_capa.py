"""Renderizador do slide de capa do Status Report.

Placeholders esperados no Slide 1 (capa) do template:

- {{CLIENTE_ID}}    -> identificacao completa (ex.: "131-ID: 0078-25 HONORP - SUPCON")
- {{COORDENADORA}}  -> responsavel pela apresentacao
- {{DATA}}          -> data de geracao formatada como dd/mm/aaaa
"""
from __future__ import annotations

from dataclasses import dataclass

from status_report.dominio.modelos import DadosRelatorio


@dataclass(frozen=True)
class RenderizadorCapa:
    nome: str = "slide_capa"

    def coletar_substituicoes(self, dados: DadosRelatorio) -> dict[str, str]:
        return {
            "{{CLIENTE_ID}}": dados.cliente.cliente_id_completo,
            "{{COORDENADORA}}": dados.cliente.coordenadora,
            "{{DATA}}": dados.data_referencia.strftime("%d/%m/%Y"),
        }
