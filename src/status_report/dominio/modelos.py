"""Modelos de dominio do Status Report.

Estes modelos sao independentes de Google APIs ou de qualquer detalhe de
infraestrutura. Eles trafegam entre as camadas de aplicacao e renderizacao.
"""
from __future__ import annotations

import re

from dataclasses import dataclass, field
from datetime import date, datetime


def _sanitizar_nome_arquivo(texto: str) -> str:
    """Remove caracteres invalidos em nomes de arquivo no Windows/Drive."""
    return re.sub(r'[\\/:*?"<>|]+', "-", texto).strip()


@dataclass(frozen=True)
class ClienteFila:
    """Linha da Fila_StatusReport que indica um cliente a ser processado."""

    nome_curto: str
    cliente_id_completo: str
    coordenadora: str
    spreadsheet_origem_id: str
    nome_pdf_customizado: str = ""
    email_coordenadora: str = ""
    codigo_cliente: str = ""
    nr_seq_cliente: str = ""
    nr_seq_proj: str = ""
    nome_projeto: str = ""

    def nome_arquivo_pdf(self, data_referencia: date) -> str:
        if self.nome_pdf_customizado:
            return self.nome_pdf_customizado
        data_iso = data_referencia.isoformat()
        projeto = (self.nome_projeto or self.cliente_id_completo).strip()
        projeto = _sanitizar_nome_arquivo(projeto)
        cliente = _sanitizar_nome_arquivo(self.nome_curto.strip())
        return f"Status Report - {cliente} - {projeto} - {data_iso}"


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
    caminhos_locais: list[str] = field(default_factory=list)


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
class ProjetoOracle:
    """Projeto ativo de um cliente vindo do ERP (Oracle proj_projeto)."""

    nr_seq_proj: int
    titulo: str

    def rotulo(self) -> str:
        return f"{self.titulo} (#{self.nr_seq_proj})"


@dataclass(frozen=True)
class LinhaHorasPlanejado:
    """Uma linha 'planejada' do Controle de Horas (nivel cronograma).

    Cada `proj_cronograma` traz o total de horas previstas/realizadas e a
    distribuicao mensal uniforme (previsto / n. de meses da vigencia).
    """

    nome_cliente: str
    nr_seq_proj: int
    nome_projeto: str
    seq_crono: int
    objetivo_cronograma: str
    dt_inicio: datetime | None
    dt_fim: datetime | None
    horas_previstas_total: float
    horas_realizado_total: float
    qt_meses: int
    horas_previstas_mes: float


@dataclass(frozen=True)
class LinhaHorasRealizado:
    """Uma linha 'realizada' do Controle de Horas por analista/funcao/mes."""

    nr_seq_proj: int
    seq_crono: int
    mes: str
    cd_executor: int
    analista: str
    funcao: str
    horas_trabalhadas: float


@dataclass(frozen=True)
class LinhaHorasPrevistoEtapa:
    """Previsto de uma etapa do cronograma (Consulta C), com funcao inferida."""

    nr_seq_proj: int
    seq_crono: int
    objetivo_cronograma: str
    crono_inicio: datetime | None
    crono_fim: datetime | None
    seq_etapa: int
    ds_atividade: str
    horas_previstas: float
    dt_inicio_prev: datetime | None
    dt_fim_prev: datetime | None
    funcao: str


@dataclass(frozen=True)
class LinhaMensalHoras:
    """Previsto x Executado de um mes (MM/YYYY)."""

    mes: str
    previsto: float
    executado: float

    @property
    def saldo(self) -> float:
        return round(self.previsto - self.executado, 2)


@dataclass(frozen=True)
class BlocoAnalistaHoras:
    """Horas de um analista (executado por mes) para o slide de analistas."""

    analista: str
    funcao: str
    cd_executor: int
    meses: list[LinhaMensalHoras]
    total_executado: float


@dataclass(frozen=True)
class ControleHoras:
    """Dados agregados do Controle de Horas de um projeto (prontos p/ slide)."""

    nome_cliente: str
    nr_seq_proj: int
    nome_projeto: str
    coordenador: str
    vigencia_inicio: datetime | None
    vigencia_fim: datetime | None
    previsto_total: float
    realizado_total: float
    realizado_por_funcao: dict[str, float]
    previsto_por_funcao: dict[str, float]
    meses: list[LinhaMensalHoras]
    meses_vigencia: list[str]
    mensal_por_funcao: dict[str, list[LinhaMensalHoras]]
    analistas: list[BlocoAnalistaHoras]

    @property
    def saldo_total(self) -> float:
        return round(self.previsto_total - self.realizado_total, 2)


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
