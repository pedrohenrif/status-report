"""Servico para buscar clientes da coordenadora via planilha + Google Calendar.

Fluxo:
1. Le a aba Coord_Status_Report (somente dados da coordenadora).
2. Le o calendario da coordenadora no dia e filtra eventos de Status Report.
3. Cruza os eventos com a aba Clientes pelo codigo numerico.
4. Usa o titulo do evento como fonte do ID completo na capa do slide.
"""
from __future__ import annotations

from status_report.configuracao import Configuracoes
from status_report.dominio.modelos import ClienteFila
from status_report.infraestrutura.repositorio_calendario import (
    extrair_cliente_id_do_evento,
    extrair_codigo_cliente,
)
from status_report.infraestrutura.repositorio_clientes import (
    _eh_verdadeiro,
    carregar_cadastro_clientes,
    indice_por_codigo,
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
) -> tuple[str, str]:
    """Retorna (email, nome_coordenadora).

    Raises:
        CoordinadoraNaoEncontrada: se o nome nao for localizado na planilha.
    """
    linhas = ler_intervalo(
        sheets=sheets,
        spreadsheet_id=configuracoes.id_planilha_principal,
        intervalo=configuracoes.intervalo_coordenadoras,
    )

    nome_normalizado = nome_coordenadora.strip().lower()
    todos_nomes: set[str] = set()
    email_encontrado = ""

    for linha in linhas:
        nome_col = _celula(linha, 0)
        if nome_col:
            todos_nomes.add(nome_col)

        if nome_col.strip().lower() != nome_normalizado:
            continue
        if not _eh_verdadeiro(_celula(linha, 1)):
            continue
        email_encontrado = _celula(linha, 2)

    if not email_encontrado:
        nomes_lista = sorted(n for n in todos_nomes if n)
        similares = _sugerir_similares(nome_normalizado, nomes_lista)
        raise CoordinadoraNaoEncontrada(nome_coordenadora, nomes_lista, similares)

    return email_encontrado, nome_coordenadora.strip()


def montar_clientes_dos_eventos(
    sheets,
    configuracoes: Configuracoes,
    titulos_eventos: list[str],
    nome_coordenadora: str,
    email_coordenadora: str,
) -> list[ClienteFila]:
    """Monta ClienteFila a partir dos eventos do calendario + aba Clientes."""
    cadastro = indice_por_codigo(
        carregar_cadastro_clientes(sheets, configuracoes, apenas_ativos=True)
    )

    resultado: list[ClienteFila] = []
    for titulo in titulos_eventos:
        codigo = extrair_codigo_cliente(titulo)
        if not codigo:
            continue
        registro = cadastro.get(codigo)
        if registro is None:
            continue

        cliente_id_evento = extrair_cliente_id_do_evento(titulo)
        cliente_id_completo = cliente_id_evento or registro.cliente_id_completo

        resultado.append(
            ClienteFila(
                nome_curto=registro.nome_curto,
                cliente_id_completo=cliente_id_completo,
                coordenadora=nome_coordenadora,
                spreadsheet_origem_id=configuracoes.id_planilha_principal,
                nome_pdf_customizado=registro.nome_pdf_customizado,
                email_coordenadora=email_coordenadora,
            )
        )

    return resultado


def _celula(linha: list[str], idx: int) -> str:
    if idx >= len(linha) or linha[idx] is None:
        return ""
    return str(linha[idx]).strip()


def _sugerir_similares(nome_buscado: str, nomes_existentes: list[str]) -> list[str]:
    partes = set(nome_buscado.split())
    return [
        nome
        for nome in nomes_existentes
        if any(parte in nome.lower() for parte in partes)
    ]
