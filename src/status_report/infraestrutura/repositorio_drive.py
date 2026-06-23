"""Operacoes na Google Drive API: copia, exporta apresentacoes e publica."""
from __future__ import annotations

import io
import re
from datetime import date
from pathlib import Path

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

_MIME_GSLIDES = "application/vnd.google-apps.presentation"
_MIME_PPTX = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)
_MIME_PDF = "application/pdf"


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


def exportar_apresentacao(drive, id_apresentacao: str, mime_type: str) -> bytes:
    """Exporta apresentacao Google Slides para o MIME informado."""
    buffer = io.BytesIO()
    request = drive.files().export_media(
        fileId=id_apresentacao,
        mimeType=mime_type,
    )
    downloader = MediaIoBaseDownload(buffer, request)
    concluido = False
    while not concluido:
        _, concluido = downloader.next_chunk()
    return buffer.getvalue()


def salvar_bytes_local(conteudo: bytes, caminho: Path) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)
    return caminho.resolve()


def baixar_apresentacoes_locais(
    drive,
    id_apresentacao: str,
    pasta_base: Path,
    data_referencia: date,
    nome_arquivo: str,
) -> tuple[list[Path], list[str]]:
    """Exporta PDF e PPTX completos. Retorna (arquivos salvos, avisos)."""
    pasta_destino = pasta_base / data_referencia.isoformat()
    nome_base = _nome_arquivo_seguro(nome_arquivo)
    salvos: list[Path] = []
    avisos: list[str] = []

    formatos = (
        ("pdf", _MIME_PDF, "PDF"),
        ("pptx", _MIME_PPTX, "PowerPoint"),
    )
    for extensao, mime_type, rotulo in formatos:
        destino = pasta_destino / f"{nome_base}.{extensao}"
        try:
            conteudo = exportar_apresentacao(drive, id_apresentacao, mime_type)
            salvos.append(salvar_bytes_local(conteudo, destino))
        except HttpError as erro:
            if _eh_limite_exportacao(erro):
                avisos.append(
                    f"{rotulo}: apresentacao completa grande demais para exportar "
                    f"(limite do Google). Edite online pelo link do Drive."
                )
            else:
                avisos.append(f"{rotulo}: falha na exportacao ({erro})")

    return salvos, avisos


def _eh_limite_exportacao(erro: BaseException) -> bool:
    if not isinstance(erro, HttpError):
        return False
    texto = str(erro).lower()
    return "exportsizelimitexceeded" in texto or "too large to be exported" in texto


def _nome_arquivo_seguro(nome: str) -> str:
    limpo = re.sub(r'[<>:"/\\|?*]', "-", (nome or "").strip())
    return limpo or "status-report"
