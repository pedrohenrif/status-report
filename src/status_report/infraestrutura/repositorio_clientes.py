"""Cadastro centralizado de clientes (aba `Clientes`).

Separado da aba de coordenadoras. O codigo numerico (ex.: 131) e usado para
cruzar com os eventos do Google Calendar.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from status_report.configuracao import Configuracoes
from status_report.infraestrutura.repositorio_planilha import ler_intervalo

_VALORES_VERDADEIROS = {"1", "true", "verdadeiro", "sim", "ativo", "yes", "y"}


@dataclass(frozen=True)
class CadastroCliente:
    codigo_cliente: str
    nome_curto: str
    cliente_id_completo: str
    nome_pdf_customizado: str = ""
    nr_seq_cliente: str = ""


def carregar_cadastro_clientes(
    sheets,
    configuracoes: Configuracoes,
    *,
    apenas_ativos: bool = True,
) -> list[CadastroCliente]:
    """Le a aba Clientes e retorna os registros cadastrados."""
    linhas = ler_intervalo(
        sheets=sheets,
        spreadsheet_id=configuracoes.id_planilha_principal,
        intervalo=configuracoes.intervalo_cadastro_clientes,
    )
    clientes: list[CadastroCliente] = []
    for linha in linhas:
        cliente = _converter_linha(linha)
        if cliente is None:
            continue
        if apenas_ativos and not _eh_verdadeiro(_celula(linha, 4)):
            continue
        clientes.append(cliente)
    return clientes


def indice_por_codigo(clientes: list[CadastroCliente]) -> dict[str, CadastroCliente]:
    return {c.codigo_cliente: c for c in clientes}


def cliente_da_linha(linha: list[str]) -> CadastroCliente | None:
    """Converte uma linha bruta da aba Clientes."""
    codigo = _normalizar_codigo(_celula(linha, 0))
    nome_curto = _celula(linha, 1)
    if not codigo or not nome_curto:
        return None
    cliente_id_completo = _celula(linha, 2) or nome_curto
    nome_pdf = _celula(linha, 3)
    nr_seq_cliente = _normalizar_codigo(_celula(linha, 6))
    return CadastroCliente(
        codigo_cliente=codigo,
        nome_curto=nome_curto,
        cliente_id_completo=cliente_id_completo,
        nome_pdf_customizado=nome_pdf,
        nr_seq_cliente=nr_seq_cliente,
    )


def _converter_linha(linha: list[str]) -> CadastroCliente | None:
    return cliente_da_linha(linha)


def _normalizar_codigo(bruto: str) -> str:
    texto = (bruto or "").strip()
    match = re.match(r"^(\d+)", texto)
    return match.group(1) if match else texto


def _celula(linha: list[str], indice: int) -> str:
    if indice >= len(linha) or linha[indice] is None:
        return ""
    return str(linha[indice]).strip()


def _eh_verdadeiro(valor: str) -> bool:
    return valor.lower() in _VALORES_VERDADEIROS
