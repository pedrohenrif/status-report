"""Carregamento e validacao das configuracoes do projeto.

Centraliza tudo que vem do `.env` em um unico objeto imutavel `Configuracoes`,
para que o restante do projeto consuma apenas tipos do dominio.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Configuracoes:
    arquivo_service_account: str
    email_service_account: str
    usuario_delegado: str
    id_planilha_principal: str
    id_apresentacao_modelo: str
    id_pasta_saida: str
    intervalo_fila_clientes: str
    intervalo_dados_relatorio: str
    intervalo_indice_projetos: str
    fuso_horario: str
    rodar_apenas_dias_uteis: bool
    modo_simulacao: bool

    def validar(self) -> None:
        caminho = Path(self.arquivo_service_account)
        if not caminho.exists():
            raise FileNotFoundError(
                f"Arquivo da service account nao encontrado: {caminho}"
            )


def carregar_configuracoes() -> Configuracoes:
    load_dotenv()
    return Configuracoes(
        arquivo_service_account=_obrigatoria("GOOGLE_SERVICE_ACCOUNT_FILE"),
        email_service_account=os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "").strip(),
        usuario_delegado=os.getenv("GOOGLE_DELEGATED_USER", "").strip(),
        id_planilha_principal=_obrigatoria("GOOGLE_SPREADSHEET_ID"),
        id_apresentacao_modelo=_obrigatoria("GOOGLE_TEMPLATE_PRESENTATION_ID"),
        id_pasta_saida=_obrigatoria("GOOGLE_OUTPUT_FOLDER_ID"),
        intervalo_fila_clientes=os.getenv(
            "GOOGLE_CLIENT_QUEUE_RANGE", "Fila_StatusReport!A2:F"
        ),
        intervalo_dados_relatorio=os.getenv(
            "GOOGLE_DATA_RANGE", "Agenda da Semana!A1:G200"
        ),
        intervalo_indice_projetos=os.getenv(
            "GOOGLE_PROJECTS_INDEX_RANGE", "Projetos_Funcionais!A1:B300"
        ),
        fuso_horario=os.getenv("TIMEZONE", "America/Sao_Paulo"),
        rodar_apenas_dias_uteis=_para_bool(os.getenv("RUN_ONLY_WEEKDAYS", "true")),
        modo_simulacao=_para_bool(os.getenv("DRY_RUN", "false")),
    )


def _obrigatoria(chave: str) -> str:
    valor = os.getenv(chave, "").strip()
    if not valor:
        raise ValueError(f"Variavel obrigatoria ausente: {chave}")
    return valor


def _para_bool(bruto: str) -> bool:
    return bruto.strip().lower() in {"1", "true", "yes", "y", "sim"}
