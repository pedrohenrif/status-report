"""Agregador de substituicoes de todos os renderizadores ativos."""
from __future__ import annotations

from status_report.dominio.modelos import DadosRelatorio
from status_report.renderizadores.protocolo import RenderizadorSlide


def coletar_substituicoes_de_todos(
    renderizadores: list[RenderizadorSlide],
    dados: DadosRelatorio,
) -> dict[str, str]:
    substituicoes_finais: dict[str, str] = {}
    for renderizador in renderizadores:
        substituicoes_do_slide = renderizador.coletar_substituicoes(dados)
        chaves_em_conflito = substituicoes_finais.keys() & substituicoes_do_slide.keys()
        if chaves_em_conflito:
            raise ValueError(
                "Conflito de placeholders entre renderizadores: "
                f"{sorted(chaves_em_conflito)}"
            )
        substituicoes_finais.update(substituicoes_do_slide)
    return substituicoes_finais
