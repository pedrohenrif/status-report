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

    print(f"\nIntervalo configurado em .env: {config.intervalo_fila_clientes}")
    nome_aba_configurada = config.intervalo_fila_clientes.split("!")[0]
    nomes_existentes = [a["properties"]["title"] for a in abas]
    if nome_aba_configurada in nomes_existentes:
        print(f"  OK - Aba '{nome_aba_configurada}' encontrada.")
    else:
        print(f"  PROBLEMA - Aba '{nome_aba_configurada}' NAO encontrada na planilha.")
        print(f"\n  Abas disponiveis: {nomes_existentes}")
        print(
            f"\n  Para corrigir, atualize GOOGLE_CLIENT_QUEUE_RANGE no .env para usar"
            f" o nome correto da aba, ou crie a aba '{nome_aba_configurada}' na planilha."
        )


if __name__ == "__main__":
    main()
