"""Acesso de leitura ao Google Calendar para busca de eventos de Status Report."""
from __future__ import annotations

import datetime
import re
from zoneinfo import ZoneInfo

_PREFIXO_STATUS_REPORT = re.compile(r"^status\s*report[-\s]*", re.IGNORECASE)


def buscar_eventos_status_report(
    calendar,
    email_coordenadora: str,
    data: datetime.date,
    fuso_horario: str,
) -> list[str]:
    """Retorna titulos dos eventos do dia que comecem com 'Status report'.

    Formato esperado: "Status report-131-ID: 0078-25-HONORP SUPCON"
    """
    tz = ZoneInfo(fuso_horario)
    inicio = datetime.datetime(data.year, data.month, data.day, 0, 0, 0, tzinfo=tz)
    fim = datetime.datetime(data.year, data.month, data.day, 23, 59, 59, tzinfo=tz)

    resultado = (
        calendar.events()
        .list(
            calendarId=email_coordenadora,
            timeMin=inicio.isoformat(),
            timeMax=fim.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    return [
        evento.get("summary", "")
        for evento in resultado.get("items", [])
        if _PREFIXO_STATUS_REPORT.match(evento.get("summary", ""))
    ]


def extrair_codigo_cliente(titulo_evento: str) -> str | None:
    """Extrai o codigo numerico do cliente do titulo do evento.

    Exemplo:
        "Status report-131-ID: 0078-25-HONORP SUPCON" -> "131"
    """
    sem_prefixo = _PREFIXO_STATUS_REPORT.sub("", titulo_evento).strip()
    match = re.match(r"^(\d+)", sem_prefixo)
    return match.group(1) if match else None


def extrair_cliente_id_do_evento(titulo_evento: str) -> str | None:
    """Extrai o identificador completo do cliente a partir do titulo do evento.

    Exemplo:
        "Status report-131-ID: 0078-25-HONORP SUPCON" -> "131-ID: 0078-25-HONORP SUPCON"
    """
    sem_prefixo = _PREFIXO_STATUS_REPORT.sub("", titulo_evento).strip()
    identificador = sem_prefixo.lstrip("-").strip()
    return identificador or None
