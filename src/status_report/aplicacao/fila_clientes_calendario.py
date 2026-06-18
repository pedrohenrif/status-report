"""Servico para buscar clientes da coordenadora via planilha + Google Calendar.

Fluxo:
1. Le a aba Fila_StatusReport e filtra as linhas da coordenadora informada.
2. Extrai o email da coordenadora dessas linhas.
3. Le o calendario da coordenadora no dia e filtra eventos de Status Report.
4. Cruza os eventos com os clientes da planilha pelo codigo numerico.
"""
from __future__ import annotations

import re
from datetime import date

from status_report.aplicacao.fila_clientes import (
    _celula,
    _converter_linha,
    _eh_verdadeiro,
)
from status_report.configuracao import Configuracoes
from status_report.dominio.modelos import ClienteFila
from status_report.infraestrutura.repositorio_calendario import (
    buscar_eventos_status_report,
    extrair_codigo_cliente,
)
from status_report.infraestrutura.repositorio_planilha import ler_intervalo


class CoordinadoraNaoEncontrada(Exception):
    """Lancada quando o nome da coordenadora nao existe na planilha."""

    def __init__(self, nome: str, nomes_disponiveis: list[str], similares: list[str]):
        self.nome = nome
        self.nomes_disponiveis = nomes_disponiveis
        self.similares = similares
        super().__init__(f"Coordenadora '{nome}' nao encontrada na planilha.")


def buscar_coordenadora_na_planilha(
    sheets,
    configuracoes: Configuracoes,
    nome_coordenadora: str,
) -> tuple[str, list[ClienteFila]]:
    """Retorna (email_coordenadora, lista_de_clientes_ativos).

    Raises:
        CoordinadoraNaoEncontrada: se o nome nao for localizado na planilha.
    """
    linhas = ler_intervalo(
        sheets=sheets,
        spreadsheet_id=configuracoes.id_planilha_principal,
        intervalo=configuracoes.intervalo_fila_clientes,
    )

    nome_normalizado = nome_coordenadora.strip().lower()
    todos_nomes: set[str] = set()
    clientes: list[ClienteFila] = []
    email_encontrado = ""

    for linha in linhas:
        nome_col = _celula(linha, 3)
        if nome_col:
            todos_nomes.add(nome_col)

        if nome_col.strip().lower() != nome_normalizado:
            continue
        if not _eh_verdadeiro(_celula(linha, 1)):
            continue

        cliente = _converter_linha(linha, configuracoes.id_planilha_principal)
        if cliente:
            clientes.append(cliente)
            if not email_encontrado:
                email_encontrado = _celula(linha, 6)

    if not clientes:
        nomes_lista = sorted(n for n in todos_nomes if n)
        similares = _sugerir_similares(nome_normalizado, nomes_lista)
        raise CoordinadoraNaoEncontrada(nome_coordenadora, nomes_lista, similares)

    return email_encontrado, clientes


def filtrar_clientes_por_eventos(
    clientes: list[ClienteFila],
    titulos_eventos: list[str],
) -> list[ClienteFila]:
    """Retorna apenas os clientes que possuem evento no calendario do dia."""
    codigos_eventos: set[str] = set()
    for titulo in titulos_eventos:
        codigo = extrair_codigo_cliente(titulo)
        if codigo:
            codigos_eventos.add(codigo)

    if not codigos_eventos:
        return []

    resultado: list[ClienteFila] = []
    for cliente in clientes:
        match = re.match(r"^(\d+)", cliente.nome_curto)
        if match and match.group(1) in codigos_eventos:
            resultado.append(cliente)

    return resultado


def _sugerir_similares(nome_buscado: str, nomes_existentes: list[str]) -> list[str]:
    """Retorna nomes parecidos para sugerir ao usuario."""
    partes = set(nome_buscado.split())
    return [
        nome
        for nome in nomes_existentes
        if any(parte in nome.lower() for parte in partes)
    ]
