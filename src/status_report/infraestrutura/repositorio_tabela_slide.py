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

# Dimensoes em EMU (1 polegada = 914400 EMU). Slide widescreen padrao = 10 x 5.625".
_POL = 914400
_LARGURA_SLIDE_PADRAO_POLEGADAS = 10.0
_ALTURA_SLIDE_PADRAO_POLEGADAS = 5.625
_MARGEM_LATERAL_PADRAO_POLEGADAS = 0.50
_Y_PADRAO_POLEGADAS = 1.95
_MARGEM_INFERIOR_PADRAO_POLEGADAS = 0.38
_ALTURA_CABECALHO_POLEGADAS = 0.28
_FONTE_CABECALHO_PT = 8.0
_FONTE_DADOS_PT = 7.5

# Minimo exigido pela Slides API: 32 pt (~0,444 polegadas).
_LARGURA_MINIMA_POLEGADAS = 406400 / _POL

# Cores (rgb 0..1)
COR_CABECALHO = {"red": 0.102, "green": 0.235, "blue": 0.431}  # azul GHR
COR_BRANCO = {"red": 1.0, "green": 1.0, "blue": 1.0}
COR_ZEBRA = {"red": 0.949, "green": 0.957, "blue": 0.965}  # cinza muito claro
COR_TEXTO = {"red": 0.13, "green": 0.13, "blue": 0.13}
COR_VERDE = {"red": 0.102, "green": 0.478, "blue": 0.290}
COR_LARANJA = {"red": 0.827, "green": 0.329, "blue": 0.0}
COR_VERMELHO = {"red": 0.753, "green": 0.227, "blue": 0.169}


@dataclass(frozen=True)
class LayoutTabela:
    x_polegadas: float = _MARGEM_LATERAL_PADRAO_POLEGADAS
    y_polegadas: float = _Y_PADRAO_POLEGADAS
    largura_polegadas: float = _LARGURA_SLIDE_PADRAO_POLEGADAS - 2 * _MARGEM_LATERAL_PADRAO_POLEGADAS
    altura_slide_polegadas: float = _ALTURA_SLIDE_PADRAO_POLEGADAS
    margem_inferior_polegadas: float = _MARGEM_INFERIOR_PADRAO_POLEGADAS

    @classmethod
    def from_dict(cls, dados: dict[str, float]) -> LayoutTabela:
        return cls(
            x_polegadas=dados["x_polegadas"],
            y_polegadas=dados["y_polegadas"],
            largura_polegadas=dados["largura_polegadas"],
            altura_slide_polegadas=dados["altura_slide_polegadas"],
            margem_inferior_polegadas=dados.get(
                "margem_inferior_polegadas", _MARGEM_INFERIOR_PADRAO_POLEGADAS
            ),
        )


@dataclass(frozen=True)
class PlantaTabela:
    """Descreve uma tabela a ser criada em um slide."""

    table_object_id: str
    slide_object_id: str
    cabecalhos: list[str]
    linhas: list[list[str]]
    larguras_polegadas: list[float]
    cor_status: dict[str, float]
    layout: LayoutTabela = field(default_factory=LayoutTabela)
    imagens_para_remover: list[str] = field(default_factory=list)


def requests_estrutura(planta: PlantaTabela) -> tuple[list[dict], list[dict]]:
    """Retorna (requests_criacao, requests_dimensoes)."""
    layout = planta.layout
    requests_criacao: list[dict] = []
    requests_dimensoes: list[dict] = []

    for object_id in planta.imagens_para_remover:
        requests_criacao.append({"deleteObject": {"objectId": object_id}})

    n_linhas = len(planta.linhas) + 1
    n_colunas = len(planta.cabecalhos)
    altura_tabela = _calcular_altura_tabela(len(planta.linhas), layout)
    altura_linha_dados = _altura_linha_dados(len(planta.linhas), altura_tabela)

    requests_criacao.append(
        {
            "createTable": {
                "objectId": planta.table_object_id,
                "elementProperties": {
                    "pageObjectId": planta.slide_object_id,
                    "size": {
                        "width": {
                            "magnitude": int(layout.largura_polegadas * _POL),
                            "unit": "EMU",
                        },
                        "height": {
                            "magnitude": int(altura_tabela * _POL),
                            "unit": "EMU",
                        },
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": int(layout.x_polegadas * _POL),
                        "translateY": int(layout.y_polegadas * _POL),
                        "unit": "EMU",
                    },
                },
                "rows": n_linhas,
                "columns": n_colunas,
            }
        }
    )

    magnitudes = _magnitudes_colunas(planta.larguras_polegadas, layout.largura_polegadas)
    for indice, magnitude in enumerate(magnitudes):
        requests_dimensoes.append(
            {
                "updateTableColumnProperties": {
                    "objectId": planta.table_object_id,
                    "columnIndices": [indice],
                    "tableColumnProperties": {
                        "columnWidth": {"magnitude": magnitude, "unit": "EMU"}
                    },
                    "fields": "columnWidth",
                }
            }
        )

    requests_dimensoes.extend(
        _altura_linha(
            planta.table_object_id,
            linha_inicio=0,
            linha_fim=1,
            altura_polegadas=_ALTURA_CABECALHO_POLEGADAS,
        )
    )
    if len(planta.linhas) > 0:
        requests_dimensoes.extend(
            _altura_linha(
                planta.table_object_id,
                linha_inicio=1,
                linha_fim=n_linhas,
                altura_polegadas=altura_linha_dados,
            )
        )

    return requests_criacao, requests_dimensoes


def requests_conteudo(planta: PlantaTabela) -> list[dict]:
    """Requests da 2a fase: preencher textos e aplicar estilos/cores."""
    requests: list[dict] = []
    table_id = planta.table_object_id
    n_colunas = len(planta.cabecalhos)

    n_linhas = len(planta.linhas) + 1

    requests.append(
        {
            "updateTableCellProperties": {
                "objectId": table_id,
                "tableRange": {
                    "location": {"rowIndex": 0, "columnIndex": 0},
                    "rowSpan": n_linhas,
                    "columnSpan": n_colunas,
                },
                "tableCellProperties": {"contentAlignment": "MIDDLE"},
                "fields": "contentAlignment",
            }
        }
    )

    requests.append(_fundo_celula(table_id, 0, 0, 1, n_colunas, COR_CABECALHO))

    for indice_linha in range(1, len(planta.linhas) + 1):
        if indice_linha % 2 == 0:
            requests.append(
                _fundo_celula(table_id, indice_linha, 0, 1, n_colunas, COR_ZEBRA)
            )

    for coluna, titulo in enumerate(planta.cabecalhos):
        requests.append(_inserir_texto(table_id, 0, coluna, titulo))
        requests.append(
            _estilo_texto(
                table_id, 0, coluna, COR_BRANCO, negrito=True, tamanho=_FONTE_CABECALHO_PT
            )
        )

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
                    tamanho=_FONTE_DADOS_PT,
                )
            )

    return requests


def _magnitudes_colunas(
    larguras_polegadas: list[float], largura_total_polegadas: float
) -> list[int]:
    """Converte larguras para EMU garantindo soma exata (Slides usa soma das colunas)."""
    escaladas = _escalar_larguras_colunas(larguras_polegadas, largura_total_polegadas)
    alvo = int(largura_total_polegadas * _POL)
    magnitudes = [
        int(max(largura, _LARGURA_MINIMA_POLEGADAS) * _POL) for largura in escaladas
    ]
    magnitudes[-1] += alvo - sum(magnitudes)
    return magnitudes


def _escalar_larguras_colunas(
    larguras: list[float], largura_tabela_polegadas: float
) -> list[float]:
    total = sum(larguras)
    if total <= 0:
        return larguras
    fator = largura_tabela_polegadas / total
    escaladas = [largura * fator for largura in larguras]
    escaladas[-1] += largura_tabela_polegadas - sum(escaladas)
    return escaladas


def _calcular_altura_tabela(n_linhas_dados: int, layout: LayoutTabela) -> float:
    altura_max = (
        layout.altura_slide_polegadas
        - layout.y_polegadas
        - layout.margem_inferior_polegadas
    )
    altura_minima = _ALTURA_CABECALHO_POLEGADAS + max(n_linhas_dados, 1) * 0.24
    return min(altura_max, altura_minima)


def _altura_linha_dados(n_linhas_dados: int, altura_tabela: float) -> float:
    if n_linhas_dados <= 0:
        return 0.24
    restante = altura_tabela - _ALTURA_CABECALHO_POLEGADAS
    return max(restante / n_linhas_dados, 0.22)


def _altura_linha(
    table_id: str,
    linha_inicio: int,
    linha_fim: int,
    altura_polegadas: float,
) -> list[dict]:
    if linha_inicio >= linha_fim:
        return []
    return [
        {
            "updateTableRowProperties": {
                "objectId": table_id,
                "rowIndices": list(range(linha_inicio, linha_fim)),
                "tableRowProperties": {
                    "minRowHeight": {
                        "magnitude": int(altura_polegadas * _POL),
                        "unit": "EMU",
                    }
                },
                "fields": "minRowHeight",
            }
        }
    ]


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
