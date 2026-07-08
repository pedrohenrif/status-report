"""Criacao de slides a partir de slides-modelo marcados por um placeholder.

Em vez de editar slides por indice fixo (5, 6, 7...), o template mantem
"slides-modelo" identificados por um marcador de texto, por exemplo
``{{MODELO_CONTROLE_HORAS}}``. O pipeline entao:

1. localiza o slide-modelo pelo marcador;
2. duplica quantas copias precisar (uma por projeto/analista/etc.);
3. preenche cada copia (texto e tabelas);
4. remove o slide-modelo original ao final.

Assim a quantidade de slides passa a ser dinamica e nao dependemos de indices.
"""
from __future__ import annotations

import re

# Marcadores de slide-modelo: {{MODELO_ALGUMA_COISA}}
_RE_MARCADOR = re.compile(r"\{\{\s*(MODELO_[A-Z0-9_]+)\s*\}\}")
# Qualquer placeholder {{...}} (para diagnostico).
_RE_PLACEHOLDER = re.compile(r"\{\{.*?\}\}")

_CAMPOS_TEXTO = (
    "slides(objectId,pageElements(objectId,"
    "shape(text(textElements(textRun(content))))))"
)


def _obter_slides(slides, presentation_id: str) -> list[dict]:
    apresentacao = (
        slides.presentations()
        .get(presentationId=presentation_id, fields=_CAMPOS_TEXTO)
        .execute()
    )
    return apresentacao.get("slides", [])


def _texto_do_slide(slide: dict) -> str:
    partes: list[str] = []
    for elemento in slide.get("pageElements", []):
        shape = elemento.get("shape")
        if not shape:
            continue
        for bloco in shape.get("text", {}).get("textElements", []):
            trecho = bloco.get("textRun", {}).get("content", "")
            if trecho:
                partes.append(trecho)
    return "".join(partes)


def mapear_slides_modelo(slides, presentation_id: str) -> dict[str, str]:
    """Retorna {NOME_DO_MARCADOR: objectId do slide} dos slides-modelo."""
    mapa: dict[str, str] = {}
    for slide in _obter_slides(slides, presentation_id):
        for achado in _RE_MARCADOR.finditer(_texto_do_slide(slide)):
            mapa.setdefault(achado.group(1), slide["objectId"])
    return mapa


def listar_placeholders(slides, presentation_id: str) -> list[tuple[int, str, list[str]]]:
    """Diagnostico: por slide, retorna (indice, objectId, [placeholders {{...}}])."""
    resultado: list[tuple[int, str, list[str]]] = []
    for indice, slide in enumerate(_obter_slides(slides, presentation_id)):
        tokens = _RE_PLACEHOLDER.findall(_texto_do_slide(slide))
        resultado.append((indice, slide["objectId"], tokens))
    return resultado


def indice_do_slide(slides, presentation_id: str, slide_id: str) -> int:
    for indice, slide in enumerate(_obter_slides(slides, presentation_id)):
        if slide["objectId"] == slide_id:
            return indice
    return -1


def duplicar_slide(slides, presentation_id: str, slide_id: str) -> str:
    """Duplica um slide e retorna o objectId da copia."""
    resposta = (
        slides.presentations()
        .batchUpdate(
            presentationId=presentation_id,
            body={"requests": [{"duplicateObject": {"objectId": slide_id}}]},
        )
        .execute()
    )
    return resposta["replies"][0]["duplicateObject"]["objectId"]


def mover_slides(slides, presentation_id: str, slide_ids: list[str], indice: int) -> None:
    """Reposiciona os slides (na ordem dada) a partir de ``indice``."""
    if not slide_ids:
        return
    (
        slides.presentations()
        .batchUpdate(
            presentationId=presentation_id,
            body={
                "requests": [
                    {
                        "updateSlidesPosition": {
                            "slideObjectIds": slide_ids,
                            "insertionIndex": indice,
                        }
                    }
                ]
            },
        )
        .execute()
    )


def remover_slides(slides, presentation_id: str, slide_ids: list[str]) -> None:
    if not slide_ids:
        return
    (
        slides.presentations()
        .batchUpdate(
            presentationId=presentation_id,
            body={
                "requests": [
                    {"deleteObject": {"objectId": sid}} for sid in slide_ids
                ]
            },
        )
        .execute()
    )


def instanciar_modelo(
    slides, presentation_id: str, marcador: str, quantidade: int
) -> list[str]:
    """Duplica o slide-modelo ``quantidade`` vezes, na ordem, logo apos o modelo.

    Retorna os objectIds das copias (em ordem). O slide-modelo NAO e removido
    aqui — chame :func:`remover_slides` depois de preencher as copias, para que
    o marcador continue disponivel caso a geracao seja repetida.
    """
    mapa = mapear_slides_modelo(slides, presentation_id)
    modelo_id = mapa.get(marcador)
    if modelo_id is None:
        raise ValueError(
            f"Slide-modelo '{{{{{marcador}}}}}' nao encontrado no template."
        )
    if quantidade <= 0:
        return []

    copias = [duplicar_slide(slides, presentation_id, modelo_id) for _ in range(quantidade)]
    base = indice_do_slide(slides, presentation_id, modelo_id)
    mover_slides(slides, presentation_id, copias, base + 1)
    return copias
