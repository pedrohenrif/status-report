"""Orquestra a renderizacao das tabelas de Projeto Funcional nos slides.

Mapeamento dos slides (indice 0-based) definido com base no template GHR:
    - slide 6 (indice 5) -> Concluidos
    - slide 7 (indice 6) -> Pendentes
    - slide 8 (indice 7) -> Em Andamento

Tambem retorna as substituicoes de quantidade para os titulos dinamicos:
    {{QTD_CONCLUIDOS}}, {{QTD_PENDENTES}}, {{QTD_EM_ANDAMENTO}}
"""
from __future__ import annotations

import re

from status_report.dominio.modelos import (
    ItemProjetoFuncional,
    ProjetoFuncionalAgrupado,
)
from status_report.infraestrutura.repositorio_tabela_slide import (
    COR_LARANJA,
    COR_VERDE,
    COR_VERMELHO,
    PlantaTabela,
    requests_conteudo,
    requests_estrutura,
)

_CABECALHOS = [
    "#",
    "Data",
    "Módulo",
    "Função/Processo",
    "Analista",
    "Descrição",
    "Prioridade",
    "Status",
]
_LARGURAS = [0.4, 0.9, 1.0, 1.7, 1.3, 2.55, 0.8, 0.85]

_LIMITE_DESCRICAO = 140

# indice do slide (0-based) por categoria
INDICES_SLIDES = {
    "concluidos": 5,
    "pendentes": 6,
    "em_andamento": 7,
}


def renderizar_tabelas_projeto_funcional(
    slides,
    presentation_id: str,
    grupos: ProjetoFuncionalAgrupado,
    indices_slides: dict[str, int] | None = None,
) -> dict[str, str]:
    """Cria as 3 tabelas e retorna as substituicoes de quantidade dos titulos."""
    indices = indices_slides or INDICES_SLIDES
    slides_info = _obter_estrutura_slides(slides, presentation_id)

    categorias = [
        ("concluidos", grupos.concluidos, COR_VERDE),
        ("pendentes", grupos.pendentes, COR_VERMELHO),
        ("em_andamento", grupos.em_andamento, COR_LARANJA),
    ]

    plantas: list[PlantaTabela] = []
    for chave, itens, cor in categorias:
        indice = indices[chave]
        if indice >= len(slides_info):
            raise IndexError(
                f"O template tem {len(slides_info)} slides, mas o slide de "
                f"'{chave}' esperado e o indice {indice}."
            )
        info = slides_info[indice]
        plantas.append(
            PlantaTabela(
                table_object_id=f"tbl_pf_{chave}",
                slide_object_id=info["objectId"],
                cabecalhos=_CABECALHOS,
                linhas=[_linha_de_item(item) for item in itens],
                larguras_polegadas=_LARGURAS,
                cor_status=cor,
                imagens_para_remover=info["imagens"],
            )
        )

    # Fase 1: remover imagens, criar tabelas e larguras.
    estrutura: list[dict] = []
    for planta in plantas:
        estrutura.extend(requests_estrutura(planta))
    _executar(slides, presentation_id, estrutura)

    # Fase 2: preencher textos e estilos (apos as tabelas existirem).
    conteudo: list[dict] = []
    for planta in plantas:
        conteudo.extend(requests_conteudo(planta))
    _executar(slides, presentation_id, conteudo)

    return {
        "{{QTD_CONCLUIDOS}}": str(grupos.total_concluidos),
        "{{QTD_PENDENTES}}": str(grupos.total_pendentes),
        "{{QTD_EM_ANDAMENTO}}": str(grupos.total_em_andamento),
    }


def _linha_de_item(item: ItemProjetoFuncional) -> list[str]:
    return [
        item.numero,
        item.data_registro,
        item.modulo,
        item.funcao,
        item.analista,
        _limpar(item.descricao),
        item.prioridade,
        item.status,
    ]


def _limpar(texto: str) -> str:
    """Junta quebras de linha e corta descricoes longas para caber na celula."""
    normalizado = re.sub(r"\s+", " ", (texto or "").replace("\n", " ")).strip()
    if len(normalizado) > _LIMITE_DESCRICAO:
        return normalizado[: _LIMITE_DESCRICAO - 1].rstrip() + "…"
    return normalizado


def _obter_estrutura_slides(slides, presentation_id: str) -> list[dict]:
    apresentacao = (
        slides.presentations()
        .get(
            presentationId=presentation_id,
            fields="slides(objectId,pageElements(objectId,image))",
        )
        .execute()
    )
    estrutura: list[dict] = []
    for slide in apresentacao.get("slides", []):
        imagens = [
            elemento["objectId"]
            for elemento in slide.get("pageElements", [])
            if "image" in elemento
        ]
        estrutura.append({"objectId": slide["objectId"], "imagens": imagens})
    return estrutura


def _executar(slides, presentation_id: str, requests: list[dict]) -> None:
    if not requests:
        return
    (
        slides.presentations()
        .batchUpdate(presentationId=presentation_id, body={"requests": requests})
        .execute()
    )
