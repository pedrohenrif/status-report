"""Operacoes na Google Drive API: copia, exporta para PDF e publica."""
from __future__ import annotations

import io

from googleapiclient.http import MediaIoBaseUpload  # usado em publicar_pdf_na_pasta

_MIME_GSLIDES = "application/vnd.google-apps.presentation"


def copiar_apresentacao(
    drive, id_modelo: str, nome_da_copia: str, id_pasta_destino: str | None = None
) -> str:
    body: dict = {"name": nome_da_copia, "mimeType": _MIME_GSLIDES}
    if id_pasta_destino:
        body["parents"] = [id_pasta_destino]
    resposta = (
        drive.files()
        .copy(
            fileId=id_modelo,
            body=body,
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )
    return resposta["id"]


def obter_link_arquivo(drive, id_arquivo: str) -> str:
    resposta = (
        drive.files()
        .get(fileId=id_arquivo, fields="webViewLink", supportsAllDrives=True)
        .execute()
    )
    return resposta.get("webViewLink", "")


def remover_arquivo(drive, id_arquivo: str) -> None:
    drive.files().delete(fileId=id_arquivo, supportsAllDrives=True).execute()


def criar_ou_obter_subpasta(drive, id_pasta_pai: str, nome: str) -> str:
    """Retorna o ID de uma subpasta existente ou cria uma nova."""
    query = (
        f"name='{nome}' and '{id_pasta_pai}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    resultado = (
        drive.files()
        .list(q=query, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True)
        .execute()
    )
    encontrados = resultado.get("files", [])
    if encontrados:
        return encontrados[0]["id"]
    metadata = {
        "name": nome,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [id_pasta_pai],
    }
    pasta = (
        drive.files()
        .create(body=metadata, fields="id", supportsAllDrives=True)
        .execute()
    )
    return pasta["id"]
