"""Lista todas as abas disponiveis na planilha configurada no .env."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.autenticacao_google import construir_servicos_google


def main() -> None:
    config = carregar_configuracoes()
    servicos = construir_servicos_google(config)

    meta = (
        servicos.sheets.spreadsheets()
        .get(spreadsheetId=config.id_planilha_principal, fields="sheets.properties")
        .execute()
    )

    abas = meta.get("sheets", [])
    print(f"\nPlanilha ID: {config.id_planilha_principal}")
    print(f"Total de abas: {len(abas)}\n")
    print(f"{'#':<4} {'Nome da aba':<50} {'ID'}")
    print("-" * 70)
    for i, aba in enumerate(abas, 1):
        props = aba["properties"]
        print(f"{i:<4} {props['title']:<50} {props['sheetId']}")

    intervalos = [
        ("Coord_Status_Report", config.intervalo_coordenadoras),
        ("Clientes", config.intervalo_cadastro_clientes),
        ("Projetos_Funcionais", config.intervalo_indice_projetos),
    ]
    nomes_existentes = [a["properties"]["title"] for a in abas]
    for rotulo, intervalo in intervalos:
        nome_aba = intervalo.split("!")[0]
        print(f"\nIntervalo {rotulo}: {intervalo}")
        if nome_aba in nomes_existentes:
            print(f"  OK - Aba '{nome_aba}' encontrada.")
        else:
            print(f"  PROBLEMA - Aba '{nome_aba}' NAO encontrada na planilha.")
            print(f"  Abas disponiveis: {nomes_existentes}")


if __name__ == "__main__":
    main()
