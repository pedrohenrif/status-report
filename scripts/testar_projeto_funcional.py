"""Testa a leitura e o agrupamento da planilha 'Projeto Funcional'.

Use este script para validar que conseguimos:
1. acessar a planilha de um cliente,
2. detectar a aba e mapear as colunas pelo cabecalho,
3. classificar os itens em concluidos / em andamento / pendentes.

Para testar outra planilha, troque a variavel LINK abaixo (ou passe o link
como argumento na linha de comando).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from status_report.aplicacao.projeto_funcional import agrupar_por_status
from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.autenticacao_google import (
    construir_servicos_google,
)
from status_report.infraestrutura.repositorio_projeto_funcional import (
    extrair_id_planilha,
    ler_itens_projeto_funcional,
)

# Planilha de teste (Projeto Funcional de um cliente especifico)
LINK = "https://docs.google.com/spreadsheets/d/1eR-aFsMqWkmyCgbKcYVLLVeZ9A5J94IQ/edit?gid=1571195596#gid=1571195596"


def main() -> None:
    link = sys.argv[1] if len(sys.argv) > 1 else LINK

    config = carregar_configuracoes()
    servicos = construir_servicos_google(config)

    spreadsheet_id = extrair_id_planilha(link)
    print("=" * 64)
    print("  TESTE DE LEITURA - PROJETO FUNCIONAL")
    print("=" * 64)
    print(f"  Spreadsheet ID : {spreadsheet_id}")

    aba, itens = ler_itens_projeto_funcional(
        servicos.sheets, servicos.drive, spreadsheet_id
    )
    print(f"  Aba detectada  : {aba!r}")
    print(f"  Itens lidos    : {len(itens)}")

    grupos = agrupar_por_status(itens)
    print()
    print(f"  Concluidos   : {grupos.total_concluidos}")
    print(f"  Em andamento : {grupos.total_em_andamento}")
    print(f"  Pendentes    : {grupos.total_pendentes}")

    categorias = [
        ("CONCLUIDOS", grupos.concluidos, grupos.total_concluidos),
        ("EM ANDAMENTO", grupos.em_andamento, grupos.total_em_andamento),
        ("PENDENTES", grupos.pendentes, grupos.total_pendentes),
    ]
    for titulo, lista, total in categorias:
        print()
        print(f"=== {titulo} ({total} no total, exibindo {len(lista)}) ===")
        for item in lista:
            print(
                f"  [{item.numero}] {item.data_registro} | {item.modulo} | "
                f"{item.funcao} | {item.analista} | prio={item.prioridade} | "
                f"{item.status}"
            )
            if item.descricao:
                print(f"        -> {item.descricao[:90]}")

    if not itens:
        print()
        print("  Nenhum item lido. Verifique se o cabecalho tem 'Status' e 'Descricao'.")


if __name__ == "__main__":
    main()
