"""Servico responsavel por descobrir quais clientes processar no dia.

A fonte de verdade e a aba `Fila_StatusReport`. O layout esperado e:

| Col | Campo                  | Exemplo                                    |
|-----|------------------------|--------------------------------------------|
| A   | nome_curto             | "131 - Honorp"                             |
| B   | ativo                  | "TRUE"                                     |
| C   | dias_semana            | "SEG,TER,QUA,QUI,SEX"                      |
| D   | coordenadora           | "Pedro Furtado"                            |
| E   | cliente_id_completo    | "131-ID: 0078-25 HONORP - SUPCON"          |
| F   | nome_pdf_customizado   | (opcional, sobrescreve o nome padrao)      |
| G   | email                  | "pedro@ghr.com.br"                         |

Linhas com `ativo` falso ou cujo dia da semana nao bate com a data de
referencia sao ignoradas.
"""
from __future__ import annotations

from datetime import date

from status_report.configuracao import Configuracoes
from status_report.dominio.modelos import ClienteFila
from status_report.infraestrutura.repositorio_planilha import ler_intervalo


_DIAS_DA_SEMANA = {
    0: "SEG",
    1: "TER",
    2: "QUA",
    3: "QUI",
    4: "SEX",
    5: "SAB",
    6: "DOM",
}

_VALORES_VERDADEIROS = {"1", "true", "verdadeiro", "sim", "ativo", "yes", "y"}


def buscar_clientes_do_dia(
    sheets,
    configuracoes: Configuracoes,
    data_referencia: date,
) -> list[ClienteFila]:
    linhas = ler_intervalo(
        sheets=sheets,
        spreadsheet_id=configuracoes.id_planilha_principal,
        intervalo=configuracoes.intervalo_fila_clientes,
    )
    token_dia = _DIAS_DA_SEMANA[data_referencia.weekday()]

    clientes: list[ClienteFila] = []
    for linha in linhas:
        cliente = _converter_linha(linha, configuracoes.id_planilha_principal)
        if cliente is None:
            continue
        dias_permitidos = _ler_dias_permitidos(linha)
        if dias_permitidos and token_dia not in dias_permitidos:
            continue
        clientes.append(cliente)
    return clientes


def _converter_linha(linha: list[str], id_planilha_padrao: str) -> ClienteFila | None:
    nome_curto = _celula(linha, 0)
    if not nome_curto:
        return None
    if not _eh_verdadeiro(_celula(linha, 1)):
        return None
    coordenadora = _celula(linha, 3) or "-"
    cliente_id_completo = _celula(linha, 4) or nome_curto
    nome_pdf_customizado = _celula(linha, 5)
    email_coordenadora = _celula(linha, 6)
    return ClienteFila(
        nome_curto=nome_curto,
        cliente_id_completo=cliente_id_completo,
        coordenadora=coordenadora,
        spreadsheet_origem_id=id_planilha_padrao,
        nome_pdf_customizado=nome_pdf_customizado,
        email_coordenadora=email_coordenadora,
    )


def _ler_dias_permitidos(linha: list[str]) -> set[str]:
    bruto = _celula(linha, 2).upper()
    return {token.strip() for token in bruto.split(",") if token.strip()}


def _celula(linha: list[str], idx: int) -> str:
    if idx >= len(linha) or linha[idx] is None:
        return ""
    return str(linha[idx]).strip()


def _eh_verdadeiro(valor: str) -> bool:
    return valor.lower() in _VALORES_VERDADEIROS
