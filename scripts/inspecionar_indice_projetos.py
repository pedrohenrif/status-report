"""Mostra o conteudo da aba 'Projetos_Funcionais' e valida a extracao de codigo."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.autenticacao_google import (
    construir_servicos_google,
)
from status_report.infraestrutura.repositorio_indice_projetos import (
    carregar_indice_projetos,
    extrair_codigo_projeto,
)


def main() -> None:
    config = carregar_configuracoes()
    servicos = construir_servicos_google(config)

    print("=" * 64)
    print("  INSPECAO - ABA Projetos_Funcionais")
    print("=" * 64)
    print(f"  Intervalo: {config.intervalo_indice_projetos}")

    pares = carregar_indice_projetos(
        sheets=servicos.sheets,
        spreadsheet_id=config.id_planilha_principal,
        intervalo=config.intervalo_indice_projetos,
    )
    print(f"  Linhas com conteudo: {len(pares)}\n")

    for projeto, link in pares:
        codigo = extrair_codigo_projeto(projeto)
        print(f"  Projeto : {projeto!r}")
        print(f"    codigo extraido: {codigo!r}")
        print(f"    link          : {link[:70]}")
        print()


if __name__ == "__main__":
    main()
