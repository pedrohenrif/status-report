"""Leitura da aba 'Projetos_Funcionais' (indice: projeto -> link da planilha).

A aba mapeia cada projeto ao link da sua planilha de Projeto Funcional. O
casamento e feito pelo CODIGO do projeto (padrao "0078-25"), extraido tanto do
texto da coluna de projeto quanto do identificador completo do cliente/evento.
Assim, pequenas diferencas de texto (acentos, nome do cliente) nao quebram a
busca, e um mesmo cliente pode ter varios projetos.
"""
from __future__ import annotations

import re

from status_report.configuracao import Configuracoes
from status_report.infraestrutura.repositorio_planilha import ler_intervalo

# Codigo do projeto, ex.: "0078-25" (3 a 5 digitos, hifen, 2 digitos).
_RE_CODIGO_PROJETO = re.compile(r"\d{3,5}\s*-\s*\d{2}")


class ProjetoNaoEncontradoNoIndice(Exception):
    """Lancada quando o codigo do projeto nao existe na aba Projetos_Funcionais."""

    def __init__(self, codigo: str, projetos_disponiveis: list[str]):
        self.codigo = codigo
        self.projetos_disponiveis = projetos_disponiveis
        super().__init__(
            f"Projeto com codigo '{codigo}' nao encontrado na aba Projetos_Funcionais."
        )


def extrair_codigo_projeto(texto: str) -> str | None:
    """Extrai o codigo do projeto de um texto.

    Exemplos:
        "Status report-131-ID: 0078-25-HONORP SUPCON" -> "0078-25"
        "131-ID: 0078-25 GHR - SUPCON"                -> "0078-25"
    """
    correspondencia = _RE_CODIGO_PROJETO.search(texto or "")
    if not correspondencia:
        return None
    return re.sub(r"\s*", "", correspondencia.group(0))


def carregar_indice_projetos(
    sheets, spreadsheet_id: str, intervalo: str
) -> list[tuple[str, str]]:
    """Retorna a lista de (texto_do_projeto, link) da aba de indice.

    A linha de cabecalho (se houver) e ignorada naturalmente, pois nao contem
    um link valido na segunda coluna.
    """
    linhas = ler_intervalo(
        sheets=sheets,
        spreadsheet_id=spreadsheet_id,
        intervalo=intervalo,
    )
    pares: list[tuple[str, str]] = []
    for linha in linhas:
        projeto = _celula(linha, 0)
        link = _celula(linha, 1)
        if not projeto and not link:
            continue
        pares.append((projeto, link))
    return pares


def buscar_link_por_codigo_projeto(
    sheets,
    configuracoes: Configuracoes,
    codigo_projeto: str,
) -> str:
    """Busca o link da planilha de Projeto Funcional pelo codigo do projeto."""
    pares = carregar_indice_projetos(
        sheets=sheets,
        spreadsheet_id=configuracoes.id_planilha_principal,
        intervalo=configuracoes.intervalo_indice_projetos,
    )
    for projeto, link in pares:
        if extrair_codigo_projeto(projeto) == codigo_projeto and link:
            return link

    disponiveis = [p for p, _ in pares if p]
    raise ProjetoNaoEncontradoNoIndice(codigo_projeto, disponiveis)


def _celula(linha: list[str], indice: int) -> str:
    if indice >= len(linha) or linha[indice] is None:
        return ""
    return str(linha[indice]).strip()
