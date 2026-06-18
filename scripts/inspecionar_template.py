"""Inspeciona a estrutura do template (slides e elementos) via Slides API.

Mostra, para cada slide, o objectId e os elementos (imagens, tabelas, textos).
Util para confirmar quais slides recebem as tabelas (6/7/8) e o que precisa ser
removido (ex.: screenshots).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.autenticacao_google import (
    construir_servicos_google,
)


def main() -> None:
    config = carregar_configuracoes()
    servicos = construir_servicos_google(config)

    apresentacao = (
        servicos.slides.presentations()
        .get(presentationId=config.id_apresentacao_modelo)
        .execute()
    )

    slides = apresentacao.get("slides", [])
    print("=" * 64)
    print("  INSPECAO DO TEMPLATE")
    print("=" * 64)
    print(f"  Titulo : {apresentacao.get('title')!r}")
    print(f"  Slides : {len(slides)}\n")

    for indice, slide in enumerate(slides):
        print(f"--- Slide #{indice + 1} (indice {indice}) | id={slide.get('objectId')}")
        for elemento in slide.get("pageElements", []):
            tipo = _tipo_elemento(elemento)
            obj_id = elemento.get("objectId")
            resumo = _resumo_texto(elemento)
            print(f"      [{tipo}] id={obj_id} {resumo}")
        print()


def _tipo_elemento(elemento: dict) -> str:
    if "image" in elemento:
        return "IMAGEM"
    if "table" in elemento:
        linhas = elemento["table"].get("rows")
        colunas = elemento["table"].get("columns")
        return f"TABELA {linhas}x{colunas}"
    if "shape" in elemento:
        return elemento["shape"].get("shapeType", "SHAPE")
    return "OUTRO"


def _resumo_texto(elemento: dict) -> str:
    shape = elemento.get("shape", {})
    texto = shape.get("text", {})
    partes: list[str] = []
    for item in texto.get("textElements", []):
        run = item.get("textRun")
        if run and run.get("content"):
            partes.append(run["content"])
    conteudo = "".join(partes).strip().replace("\n", " ")
    return f'-> "{conteudo[:60]}"' if conteudo else ""


if __name__ == "__main__":
    main()
