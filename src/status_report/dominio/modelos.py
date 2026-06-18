"""Modelos de dominio do Status Report.

Estes modelos sao independentes de Google APIs ou de qualquer detalhe de
infraestrutura. Eles trafegam entre as camadas de aplicacao e renderizacao.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ClienteFila:
    """Linha da Fila_StatusReport que indica um cliente a ser processado."""

    nome_curto: str
    cliente_id_completo: str
    coordenadora: str
    spreadsheet_origem_id: str
    nome_pdf_customizado: str = ""
    email_coordenadora: str = ""

    def nome_arquivo_pdf(self, data_referencia: date) -> str:
        if self.nome_pdf_customizado:
            return self.nome_pdf_customizado
        data_iso = data_referencia.isoformat()
        return f"Status Report - {self.nome_curto} - {data_iso}"


@dataclass(frozen=True)
class DadosRelatorio:
    """Conjunto de dados que alimentam todos os renderizadores de slides."""

    cliente: ClienteFila
    data_referencia: date
    dados_extras: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ResultadoExecucao:
    """Resultado de processamento de um cliente no pipeline diario."""

    cliente: str
    sucesso: bool
    url_pdf: str
    mensagem: str


@dataclass(frozen=True)
class ItemProjetoFuncional:
    """Uma linha da planilha 'Projeto Funcional' de um cliente.

    Apenas os campos usados nos slides sao mantidos; colunas extras da
    planilha de origem (Nivel, Data Entrega, Avaliacao, etc.) sao ignoradas.
    """

    numero: str
    data_registro: str
    modulo: str
    funcao: str
    analista: str
    descricao: str
    prioridade: str
    status: str


@dataclass(frozen=True)
class ProjetoFuncionalAgrupado:
    """Itens do Projeto Funcional separados por status.

    As listas ja vem truncadas ao limite de exibicao do slide, enquanto os
    campos `total_*` guardam a contagem real (usada no titulo dinamico).
    """

    concluidos: list[ItemProjetoFuncional]
    em_andamento: list[ItemProjetoFuncional]
    pendentes: list[ItemProjetoFuncional]
    total_concluidos: int
    total_em_andamento: int
    total_pendentes: int
