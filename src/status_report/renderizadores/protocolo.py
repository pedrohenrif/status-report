"""Contrato comum a todos os renderizadores de slides."""
from __future__ import annotations

from typing import Protocol

from status_report.dominio.modelos import DadosRelatorio


class RenderizadorSlide(Protocol):
    nome: str

    def coletar_substituicoes(self, dados: DadosRelatorio) -> dict[str, str]:
        """Retorna o mapa de placeholders a aplicar no slide deste renderizador."""
        ...
