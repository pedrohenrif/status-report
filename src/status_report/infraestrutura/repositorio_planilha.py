"""Acesso de leitura ao Google Sheets."""
from __future__ import annotations

from googleapiclient.errors import HttpError


class IntervaloPlanilhaInvalido(RuntimeError):
    """Erro lancado quando o intervalo configurado nao existe na planilha."""


def ler_intervalo(sheets, spreadsheet_id: str, intervalo: str) -> list[list[str]]:
    try:
        resposta = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=intervalo)
            .execute()
        )
    except HttpError as erro:
        if erro.resp.status == 400 and "Unable to parse range" in str(erro):
            raise IntervaloPlanilhaInvalido(
                f"Intervalo '{intervalo}' nao encontrado na planilha "
                f"'{spreadsheet_id}'. Verifique se a aba existe e se o nome esta correto."
            ) from erro
        raise
    return resposta.get("values", [])
