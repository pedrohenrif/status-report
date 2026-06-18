"""Autenticacao via service account e construcao dos clientes Google."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from status_report.configuracao import Configuracoes


ESCOPOS_GOOGLE = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/presentations",
]

ESCOPOS_CALENDARIO = [
    "https://www.googleapis.com/auth/calendar.readonly",
]


@dataclass(frozen=True)
class ServicosGoogle:
    sheets: Any
    slides: Any
    drive: Any


def construir_servicos_google(configuracoes: Configuracoes) -> ServicosGoogle:
    credenciais = service_account.Credentials.from_service_account_file(
        configuracoes.arquivo_service_account,
        scopes=ESCOPOS_GOOGLE,
    )
    if configuracoes.usuario_delegado:
        credenciais = credenciais.with_subject(configuracoes.usuario_delegado)
    return ServicosGoogle(
        sheets=build("sheets", "v4", credentials=credenciais, cache_discovery=False),
        slides=build("slides", "v1", credentials=credenciais, cache_discovery=False),
        drive=build("drive", "v3", credentials=credenciais, cache_discovery=False),
    )


def construir_servico_calendario(configuracoes: Configuracoes, email_usuario: str):
    """Cria cliente Google Calendar impersonando email_usuario via DWD."""
    credenciais = service_account.Credentials.from_service_account_file(
        configuracoes.arquivo_service_account,
        scopes=ESCOPOS_CALENDARIO,
    ).with_subject(email_usuario)
    return build("calendar", "v3", credentials=credenciais, cache_discovery=False)
