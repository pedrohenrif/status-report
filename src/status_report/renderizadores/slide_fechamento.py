"""Renderizador do slide de fechamento do Status Report.

Placeholders esperados no Slide 17 (fechamento) do template:

- {{EMAIL_COORDENADORA}} -> e-mail da coordenadora responsavel
- {{DATA}}               -> reutiliza o mesmo placeholder da capa (substituido globalmente)
"""
from __future__ import annotations

from dataclasses import dataclass

from status_report.dominio.modelos import DadosRelatorio


@dataclass(frozen=True)
class RenderizadorFechamento:
    nome: str = "slide_fechamento"

    def coletar_substituicoes(self, dados: DadosRelatorio) -> dict[str, str]:
        return {
            "{{EMAIL_COORDENADORA}}": dados.cliente.email_coordenadora,
        }
