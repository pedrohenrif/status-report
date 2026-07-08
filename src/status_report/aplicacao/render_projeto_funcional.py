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
from status_report.infraestrutura.repositorio_slides_pf import (
    calcular_layout_tabela,
    ids_elementos_removiveis,
)
from status_report.infraestrutura.repositorio_tabela_slide import (
    COR_LARANJA,
    COR_VERDE,
    COR_VERMELHO,
    LayoutTabela,
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
# #, Data, Modulo, Funcao, Analista, Descricao, Prioridade, Status
_LARGURAS = [0.42, 0.78, 0.86, 1.35, 1.05, 3.40, 0.70, 0.90]

_LIMITE_DESCRICAO = 105

# indice do slide (0-based) por categoria
INDICES_SLIDES = {
    "concluidos": 5,
    "pendentes": 6,
    "em_andamento": 7,
}


def substituicoes_quantidade_projeto_funcional(
    grupos: ProjetoFuncionalAgrupado,
) -> dict[str, str]:
    """Retorna placeholders de quantidade dos titulos dos slides 6/7/8."""
    return {
        "{{QTD_CONCLUIDOS}}": str(grupos.total_concluidos),
        "{{QTD_PENDENTES}}": str(grupos.total_pendentes),
        "{{QTD_EM_ANDAMENTO}}": str(grupos.total_em_andamento),
    }


def renderizar_tabelas_projeto_funcional(
    slides,
    presentation_id: str,
    grupos: ProjetoFuncionalAgrupado,
    indices_slides: dict[str, int] | None = None,
    slides_por_chave: dict[str, str] | None = None,
) -> None:
    """Cria as 3 tabelas nos slides de Projeto Funcional.

    ``slides_por_chave`` (chave -> objectId do slide) tem prioridade sobre
    ``indices_slides`` e e o modo usado pela geracao por marcador.
    """
    indices = indices_slides or INDICES_SLIDES
    slides_info = _obter_estrutura_slides(slides, presentation_id)
    por_id = {info["objectId"]: info for info in slides_info}

    def _info_do_slide(chave: str) -> dict:
        if slides_por_chave and chave in slides_por_chave:
            object_id = slides_por_chave[chave]
            if object_id not in por_id:
                raise KeyError(f"Slide '{object_id}' ({chave}) nao encontrado.")
            return por_id[object_id]
        indice = indices[chave]
        if indice >= len(slides_info):
            raise IndexError(
                f"O template tem {len(slides_info)} slides, mas o slide de "
                f"'{chave}' esperado e o indice {indice}."
            )
        return slides_info[indice]

    categorias = [
        ("concluidos", grupos.concluidos, COR_VERDE),
        ("pendentes", grupos.pendentes, COR_VERMELHO),
        ("em_andamento", grupos.em_andamento, COR_LARANJA),
    ]

    plantas: list[PlantaTabela] = []
    for chave, itens, cor in categorias:
        info = _info_do_slide(chave)
        plantas.append(
            PlantaTabela(
                table_object_id=f"tbl_pf_{chave}",
                slide_object_id=info["objectId"],
                cabecalhos=_CABECALHOS,
                linhas=[_linha_de_item(item) for item in itens],
                larguras_polegadas=_LARGURAS,
                cor_status=cor,
                layout=info["layout"],
                imagens_para_remover=info["elementos_removiveis"],
            )
        )

    criacao: list[dict] = []
    dimensoes: list[dict] = []
    for planta in plantas:
        reqs_criacao, reqs_dimensoes = requests_estrutura(planta)
        criacao.extend(reqs_criacao)
        dimensoes.extend(reqs_dimensoes)
    _executar(slides, presentation_id, criacao)
    _executar(slides, presentation_id, dimensoes)

    # Fase 2: preencher textos e estilos (apos as tabelas existirem).
    conteudo: list[dict] = []
    for planta in plantas:
        conteudo.extend(requests_conteudo(planta))
    _executar(slides, presentation_id, conteudo)


def preparar_slides_projeto_funcional(
    slides,
    presentation_id: str,
    *,
    incluir_tabela_exemplo: bool = True,
    indices_slides: dict[str, int] | None = None,
) -> None:
    """Remove conteudo antigo dos slides PF e opcionalmente insere tabelas de exemplo."""
    indices = indices_slides or INDICES_SLIDES
    slides_info = _obter_estrutura_slides(slides, presentation_id)

    limpeza: list[dict] = []
    for chave, indice in indices.items():
        if indice >= len(slides_info):
            raise IndexError(
                f"O template tem {len(slides_info)} slides, mas o slide de "
                f"'{chave}' esperado e o indice {indice}."
            )
        for object_id in slides_info[indice]["elementos_removiveis"]:
            limpeza.append({"deleteObject": {"objectId": object_id}})
    _executar(slides, presentation_id, limpeza)

    if not incluir_tabela_exemplo:
        return

    categorias = [
        ("concluidos", _LINHAS_EXEMPLO["concluidos"], COR_VERDE),
        ("pendentes", _LINHAS_EXEMPLO["pendentes"], COR_VERMELHO),
        ("em_andamento", _LINHAS_EXEMPLO["em_andamento"], COR_LARANJA),
    ]
    plantas: list[PlantaTabela] = []
    for chave, linhas, cor in categorias:
        indice = indices[chave]
        plantas.append(
            PlantaTabela(
                table_object_id=f"tbl_pf_exemplo_{chave}",
                slide_object_id=slides_info[indice]["objectId"],
                cabecalhos=_CABECALHOS,
                linhas=linhas,
                larguras_polegadas=_LARGURAS,
                cor_status=cor,
                layout=slides_info[indice]["layout"],
            )
        )

    criacao: list[dict] = []
    dimensoes: list[dict] = []
    for planta in plantas:
        reqs_criacao, reqs_dimensoes = requests_estrutura(planta)
        criacao.extend(reqs_criacao)
        dimensoes.extend(reqs_dimensoes)
    _executar(slides, presentation_id, criacao)
    _executar(slides, presentation_id, dimensoes)

    conteudo: list[dict] = []
    for planta in plantas:
        conteudo.extend(requests_conteudo(planta))
    _executar(slides, presentation_id, conteudo)


_LINHAS_EXEMPLO = {
    "concluidos": [
        ["1", "01/01/2024", "Financeiro", "OPS - Exemplo", "Analista", "Descricao de exemplo para ajustar a largura das colunas", "10-ALTA", "50-CONCLUÍDO"],
        ["2", "02/01/2024", "Contratos", "OPS - Exemplo 2", "Analista", "Segunda linha de exemplo", "10-ALTA", "50-CONCLUÍDO"],
        ["3", "03/01/2024", "Mensalidades", "OPS - Exemplo 3", "Analista", "Terceira linha de exemplo", "10-ALTA", "50-CONCLUÍDO"],
    ],
    "pendentes": [
        ["10", "04/01/2024", "Contas Médicas", "OPS - Pendente", "Analista", "Item pendente de exemplo", "10-ALTA", "10-PENDENTE"],
        ["11", "05/01/2024", "Mensalidades", "OPS - Pendente 2", "Analista", "Outro item pendente", "20-MÉDIA", "10-PENDENTE"],
        ["12", "06/01/2024", "Financeiro", "OPS - Pendente 3", "Analista", "Mais um pendente", "30-BAIXA", "10-PENDENTE"],
    ],
    "em_andamento": [
        ["20", "07/01/2024", "Produção", "OPS - Andamento", "Analista", "Item em andamento de exemplo", "10-ALTA", "20-EM ANDAMENTO"],
        ["21", "08/01/2024", "Financeiro", "OPS - Andamento 2", "Analista", "Segundo em andamento", "20-MÉDIA", "20-EM ANDAMENTO"],
        ["22", "09/01/2024", "Contratos", "OPS - Andamento 3", "Analista", "Terceiro em andamento", "10-ALTA", "20-EM ANDAMENTO"],
    ],
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
            fields=(
                "pageSize,"
                "slides(objectId,pageElements(objectId,transform,size,"
                "shape(text(textElements(textRun(content)))),table,image,line,elementGroup))"
            ),
        )
        .execute()
    )
    page_size = apresentacao.get("pageSize", {})
    largura_slide = page_size.get("width", {}).get("magnitude", 9144000) / 914400
    altura_slide = page_size.get("height", {}).get("magnitude", 5143500) / 914400

    estrutura: list[dict] = []
    for slide in apresentacao.get("slides", []):
        elementos = slide.get("pageElements", [])
        layout = LayoutTabela.from_dict(
            calcular_layout_tabela(largura_slide, altura_slide, elementos)
        )
        estrutura.append(
            {
                "objectId": slide["objectId"],
                "elementos_removiveis": ids_elementos_removiveis(elementos),
                "layout": layout,
            }
        )
    return estrutura


def _executar(slides, presentation_id: str, requests: list[dict]) -> None:
    if not requests:
        return
    (
        slides.presentations()
        .batchUpdate(presentationId=presentation_id, body={"requests": requests})
        .execute()
    )
