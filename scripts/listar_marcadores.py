"""Lista os placeholders e slides-modelo ({{MODELO_*}}) do template.

Use para confirmar que o marcador do slide-modelo foi detectado apos ajustar
o slide base. Exemplo:

    poetry run python scripts/listar_marcadores.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.autenticacao_google import construir_servicos_google
from status_report.infraestrutura.repositorio_drive import (
    copiar_apresentacao,
    remover_arquivo,
)
from status_report.infraestrutura.repositorio_slides_modelo import (
    listar_placeholders,
    mapear_slides_modelo,
)


def main() -> None:
    config = carregar_configuracoes()
    servicos = construir_servicos_google(config)
    template_id = config.id_apresentacao_modelo

    print(f"Template ID: {template_id}")
    # O template pode estar salvo como arquivo Office (.pptx), que a Slides API
    # nao le direto. Copiamos convertendo para Google Slides (como o pipeline),
    # lemos os marcadores e apagamos a copia.
    print("Copiando/convertendo o template para leitura...\n")
    copia_id = copiar_apresentacao(
        servicos.drive, template_id, "TEMP_LISTAR_MARCADORES"
    )
    try:
        placeholders = listar_placeholders(servicos.slides, copia_id)
        print(f"Total de slides: {len(placeholders)}\n")
        for indice, object_id, tokens in placeholders:
            marcados = " ".join(tokens) if tokens else "(sem placeholders)"
            print(f"  Slide {indice} [{object_id}]: {marcados}")

        print()
        modelos = mapear_slides_modelo(servicos.slides, copia_id)
        if modelos:
            print("Slides-modelo detectados:")
            for marcador, object_id in modelos.items():
                print(f"  {{{{{marcador}}}}} -> slide {object_id}")
        else:
            print("Nenhum slide-modelo ({{MODELO_*}}) encontrado ainda.")
            print(
                "Adicione um marcador de texto no slide base, "
                "ex.: {{MODELO_CONTROLE_HORAS}}"
            )
    finally:
        remover_arquivo(servicos.drive, copia_id)


if __name__ == "__main__":
    main()
