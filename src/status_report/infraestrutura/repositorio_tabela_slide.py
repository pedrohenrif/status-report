"""Criacao e estilizacao de tabelas em slides via Google Slides API.

A funcao principal recebe a "planta" de uma tabela (cabecalhos, linhas, cores)
e gera os requests de `batchUpdate` necessarios para:
1. apagar imagens existentes no slide (ex.: screenshots antigos),
2. criar a tabela posicionada,
3. definir larguras de coluna,
4. preencher os textos,
5. aplicar cores de fundo (cabecalho + zebra) e estilos de fonte.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Dimensoes em EMU (1 polegada = 914400 EMU). Slide widescreen padrao = 10 x 5.63".
_POL = 914400
_TABELA_X = int(0.25 * _POL)
_TABELA_Y = int(1.30 * _POL)
_TABELA_LARGURA = int(9.50 * _POL)
_TABELA_ALTURA = int(4.10 * _POL)

# Cores (rgb 0..1)
COR_CABECALHO = {"red": 0.102, "green": 0.235, "blue": 0.431}  # azul GHR
COR_BRANCO = {"red": 1.0, "green": 1.0, "blue": 1.0}
COR_ZEBRA = {"red": 0.949, "green": 0.957, "blue": 0.965}  # cinza muito claro
COR_TEXTO = {"red": 0.13, "green": 0.13, "blue": 0.13}
COR_VERDE = {"red": 0.102, "green": 0.478, "blue": 0.290}
COR_LARANJA = {"red": 0.827, "green": 0.329, "blue": 0.0}
COR_VERMELHO = {"red": 0.753, "green": 0.227, "blue": 0.169}


@dataclass(frozen=True)
class PlantaTabela:
    """Descreve uma tabela a ser criada em um slide."""

    table_object_id: str
    slide_object_id: str
    cabecalhos: list[str]
    linhas: list[list[str]]
    larguras_polegadas: list[float]
    cor_status: dict[str, float]
    imagens_para_remover: list[str] = field(default_factory=list)


def requests_estrutura(planta: PlantaTabela) -> list[dict]:
    """Requests da 1a fase: remover imagens, criar tabela e definir larguras."""
    requests: list[dict] = []

    for image_id in planta.imagens_para_remover:
        requests.append({"deleteObject": {"objectId": image_id}})

    n_linhas = len(planta.linhas) + 1  # +1 cabecalho
    n_colunas = len(planta.cabecalhos)

    requests.append(
        {
            "createTable": {
                "objectId": planta.table_object_id,
                "elementProperties": {
                    "pageObjectId": planta.slide_object_id,
                    "size": {
                        "width": {"magnitude": _TABELA_LARGURA, "unit": "EMU"},
                        "height": {"magnitude": _TABELA_ALTURA, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": _TABELA_X,
                        "translateY": _TABELA_Y,
                        "unit": "EMU",
                    },
                },
                "rows": n_linhas,
                "columns": n_colunas,
            }
        }
    )

    for indice, largura in enumerate(planta.larguras_polegadas):
        requests.append(
            {
                "updateTableColumnProperties": {
                    "objectId": planta.table_object_id,
                    "columnIndices": [indice],
                    "tableColumnProperties": {
                        "columnWidth": {
                            "magnitude": int(largura * _POL),
                            "unit": "EMU",
                        }
                    },
                    "fields": "columnWidth",
                }
            }
        )

    return requests


def requests_conteudo(planta: PlantaTabela) -> list[dict]:
    """Requests da 2a fase: preencher textos e aplicar estilos/cores."""
    requests: list[dict] = []
    table_id = planta.table_object_id
    n_colunas = len(planta.cabecalhos)

    # Fundo do cabecalho.
    requests.append(_fundo_celula(table_id, 0, 0, 1, n_colunas, COR_CABECALHO))

    # Zebra: pinta linhas de dados pares (1-based) com cinza claro.
    for indice_linha in range(1, len(planta.linhas) + 1):
        if indice_linha % 2 == 0:
            requests.append(
                _fundo_celula(table_id, indice_linha, 0, 1, n_colunas, COR_ZEBRA)
            )

    # Cabecalho: texto + estilo.
    for coluna, titulo in enumerate(planta.cabecalhos):
        requests.append(_inserir_texto(table_id, 0, coluna, titulo))
        requests.append(
            _estilo_texto(table_id, 0, coluna, COR_BRANCO, negrito=True, tamanho=8.5)
        )

    # Linhas de dados.
    indice_status = _indice_status(planta.cabecalhos)
    for desloc, linha in enumerate(planta.linhas):
        indice_linha = desloc + 1
        for coluna in range(n_colunas):
            valor = linha[coluna] if coluna < len(linha) else ""
            valor = valor if valor else " "
            requests.append(_inserir_texto(table_id, indice_linha, coluna, valor))

            eh_status = coluna == indice_status
            cor = planta.cor_status if eh_status else COR_TEXTO
            requests.append(
                _estilo_texto(
                    table_id,
                    indice_linha,
                    coluna,
                    cor,
                    negrito=eh_status,
                    tamanho=7.5,
                )
            )

    return requests


def _indice_status(cabecalhos: list[str]) -> int:
    for indice, titulo in enumerate(cabecalhos):
        if titulo.strip().lower().startswith("status"):
            return indice
    return -1


def _fundo_celula(
    table_id: str,
    linha: int,
    coluna: int,
    rowspan: int,
    colspan: int,
    cor: dict[str, float],
) -> dict:
    return {
        "updateTableCellProperties": {
            "objectId": table_id,
            "tableRange": {
                "location": {"rowIndex": linha, "columnIndex": coluna},
                "rowSpan": rowspan,
                "columnSpan": colspan,
            },
            "tableCellProperties": {
                "tableCellBackgroundFill": {
                    "solidFill": {"color": {"rgbColor": cor}}
                }
            },
            "fields": "tableCellBackgroundFill.solidFill.color",
        }
    }


def _inserir_texto(table_id: str, linha: int, coluna: int, texto: str) -> dict:
    return {
        "insertText": {
            "objectId": table_id,
            "cellLocation": {"rowIndex": linha, "columnIndex": coluna},
            "text": texto,
            "insertionIndex": 0,
        }
    }


def _estilo_texto(
    table_id: str,
    linha: int,
    coluna: int,
    cor: dict[str, float],
    negrito: bool,
    tamanho: float,
) -> dict:
    return {
        "updateTextStyle": {
            "objectId": table_id,
            "cellLocation": {"rowIndex": linha, "columnIndex": coluna},
            "textRange": {"type": "ALL"},
            "style": {
                "bold": negrito,
                "fontSize": {"magnitude": tamanho, "unit": "PT"},
                "foregroundColor": {"opaqueColor": {"rgbColor": cor}},
            },
            "fields": "bold,fontSize,foregroundColor",
        }
    }
