"""Operacoes na Google Slides API."""
from __future__ import annotations


def aplicar_substituicoes(
    slides,
    id_apresentacao: str,
    substituicoes: dict[str, str],
) -> None:
    if not substituicoes:
        return
    requisicoes = [
        {
            "replaceAllText": {
                "containsText": {"text": chave, "matchCase": True},
                "replaceText": valor,
            }
        }
        for chave, valor in substituicoes.items()
    ]
    (
        slides.presentations()
        .batchUpdate(
            presentationId=id_apresentacao,
            body={"requests": requisicoes},
        )
        .execute()
    )
