"""Regras de negocio para agrupar os itens do Projeto Funcional por status.

Status esperados na planilha (o prefixo numerico e ignorado na comparacao):
    - "10-Pendente"     -> pendentes
    - "20-Em Andamento" -> em_andamento
    - "30-Concluido"    -> concluidos
"""
from __future__ import annotations

import unicodedata

from status_report.dominio.modelos import (
    ItemProjetoFuncional,
    ProjetoFuncionalAgrupado,
)

LIMITE_POR_CATEGORIA = 12


def agrupar_por_status(
    itens: list[ItemProjetoFuncional],
    limite: int = LIMITE_POR_CATEGORIA,
) -> ProjetoFuncionalAgrupado:
    """Separa os itens em concluidos/em_andamento/pendentes.

    As listas retornadas vem truncadas em `limite`, mas os totais refletem a
    contagem real (para o titulo dinamico do slide, ex.: "Concluidos (167)").
    """
    concluidos: list[ItemProjetoFuncional] = []
    em_andamento: list[ItemProjetoFuncional] = []
    pendentes: list[ItemProjetoFuncional] = []

    for item in itens:
        categoria = _classificar(item.status)
        if categoria == "concluido":
            concluidos.append(item)
        elif categoria == "em_andamento":
            em_andamento.append(item)
        elif categoria == "pendente":
            pendentes.append(item)

    return ProjetoFuncionalAgrupado(
        concluidos=concluidos[:limite],
        em_andamento=em_andamento[:limite],
        pendentes=pendentes[:limite],
        total_concluidos=len(concluidos),
        total_em_andamento=len(em_andamento),
        total_pendentes=len(pendentes),
    )


def _classificar(status: str) -> str | None:
    n = _normalizar(status)
    if "conclu" in n:
        return "concluido"
    if "andamento" in n:
        return "em_andamento"
    if "pendente" in n:
        return "pendente"
    return None


def _normalizar(texto: str) -> str:
    texto = (texto or "").strip().lower()
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
