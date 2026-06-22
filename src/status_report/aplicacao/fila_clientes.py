"""Servico responsavel por descobrir quais clientes processar no dia (modo CLI).

A fila vem da aba `Clientes`, filtrada por `ativo` e `dias_semana`.
"""
from __future__ import annotations

from datetime import date

from status_report.configuracao import Configuracoes
from status_report.dominio.modelos import ClienteFila
from status_report.infraestrutura.repositorio_clientes import (
    _eh_verdadeiro,
    cliente_da_linha,
)
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


def buscar_clientes_do_dia(
    sheets,
    configuracoes: Configuracoes,
    data_referencia: date,
) -> list[ClienteFila]:
    linhas = ler_intervalo(
        sheets=sheets,
        spreadsheet_id=configuracoes.id_planilha_principal,
        intervalo=configuracoes.intervalo_cadastro_clientes,
    )
    token_dia = _DIAS_DA_SEMANA[data_referencia.weekday()]

    clientes: list[ClienteFila] = []
    for linha in linhas:
        if not _eh_verdadeiro(_celula(linha, 4)):
            continue
        cad = cliente_da_linha(linha)
        if cad is None:
            continue
        dias_permitidos = _ler_dias_permitidos(linha)
        if dias_permitidos and token_dia not in dias_permitidos:
            continue
        clientes.append(
            ClienteFila(
                nome_curto=cad.nome_curto,
                cliente_id_completo=cad.cliente_id_completo,
                coordenadora="-",
                spreadsheet_origem_id=configuracoes.id_planilha_principal,
                nome_pdf_customizado=cad.nome_pdf_customizado,
                email_coordenadora="",
            )
        )
    return clientes


def _ler_dias_permitidos(linha: list[str]) -> set[str]:
    bruto = _celula(linha, 5).upper()
    return {token.strip() for token in bruto.split(",") if token.strip()}


def _celula(linha: list[str], idx: int) -> str:
    if idx >= len(linha) or linha[idx] is None:
        return ""
    return str(linha[idx]).strip()
