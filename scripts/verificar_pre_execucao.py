"""Verifica todos os pre-requisitos antes da execucao completa do pipeline.

Testa:
1. Acesso de leitura a aba Fila_StatusReport (Sheets API)
2. Clientes encontrados para hoje
3. Substituicoes que serao aplicadas no template
4. Acesso de escrita na pasta de saida (Drive API)
5. Acesso ao template do Slides (Drive API) - requer liberacao do Workspace admin
"""
from __future__ import annotations

import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from status_report.aplicacao.fila_clientes import buscar_clientes_do_dia
from status_report.aplicacao.pipeline_diario import construir_data_referencia
from status_report.aplicacao.renderizacao_relatorio import coletar_substituicoes_de_todos
from status_report.configuracao import carregar_configuracoes
from status_report.dominio.modelos import DadosRelatorio
from status_report.infraestrutura.autenticacao_google import construir_servicos_google
from status_report.renderizadores.registro import RENDERIZADORES_ATIVOS


OK   = "  [OK]  "
ERRO = " [ERRO] "
AVISO = "[AVISO] "


def main() -> None:
    config = carregar_configuracoes()
    servicos = construir_servicos_google(config)
    data_ref = construir_data_referencia(config.fuso_horario)

    print("=" * 60)
    print("  VERIFICACAO PRE-EXECUCAO - STATUS REPORT")
    print("=" * 60)
    print(f"  Data de referencia : {data_ref.strftime('%d/%m/%Y')} ({_dia_semana(data_ref)})")
    print(f"  Service account    : {config.email_service_account}")
    print()

    # ------------------------------------------------------------------
    # 1. Fila de clientes (Sheets API)
    # ------------------------------------------------------------------
    print("1. FILA DE CLIENTES (Sheets API)")
    try:
        clientes = buscar_clientes_do_dia(
            sheets=servicos.sheets,
            configuracoes=config,
            data_referencia=data_ref,
        )
        if clientes:
            print(f"{OK} {len(clientes)} cliente(s) na fila para hoje:")
            for c in clientes:
                print(f"     - {c.nome_curto} | coordenadora: {c.coordenadora}")
                print(f"       ID completo : {c.cliente_id_completo}")
                print(f"       Nome do PDF : {c.nome_arquivo_pdf(data_ref)}")
        else:
            print(f"{AVISO} Nenhum cliente na fila para hoje ({_dia_semana(data_ref)}).")
            print("       Use --force-run para testar com qualquer data.")
    except Exception as e:
        print(f"{ERRO} Falha ao ler fila: {e}")
        clientes = []
    print()

    # ------------------------------------------------------------------
    # 2. Substituicoes que serao aplicadas
    # ------------------------------------------------------------------
    print("2. SUBSTITUICOES DO TEMPLATE (renderizadores ativos)")
    if clientes:
        cliente = clientes[0]
        dados = DadosRelatorio(cliente=cliente, data_referencia=data_ref)
        try:
            subs = coletar_substituicoes_de_todos(RENDERIZADORES_ATIVOS, dados)
            print(f"{OK} {len(subs)} placeholder(s) serao substituidos:")
            for placeholder, valor in subs.items():
                print(f"     {placeholder!r:30s} -> {valor!r}")
        except Exception as e:
            print(f"{ERRO} Erro ao coletar substituicoes: {e}")
    else:
        print(f"{AVISO} Sem clientes para simular substituicoes.")
    print()

    # ------------------------------------------------------------------
    # 3. Pasta de saida (Drive API - escrita)
    # ------------------------------------------------------------------
    print("3. PASTA DE SAIDA (Drive API)")
    try:
        meta_pasta = (
            servicos.drive.files()
            .get(fileId=config.id_pasta_saida, fields="id,name,mimeType", supportsAllDrives=True)
            .execute()
        )
        print(f"{OK} Pasta acessivel: {meta_pasta.get('name')!r}")
        print(f"     ID: {config.id_pasta_saida}")
    except Exception as e:
        if "404" in str(e):
            print(f"{ERRO} Pasta NAO encontrada ou sem acesso.")
            print(f"     ID configurado: {config.id_pasta_saida}")
            print("     Compartilhe a pasta com a service account como Editor.")
        else:
            print(f"{ERRO} Erro ao acessar pasta: {e}")
    print()

    # ------------------------------------------------------------------
    # 4. Template do Slides (Drive API - leitura/copia)
    # ------------------------------------------------------------------
    print("4. TEMPLATE DO SLIDES (Drive API)")
    try:
        meta_template = (
            servicos.drive.files()
            .get(fileId=config.id_apresentacao_modelo, fields="id,name,mimeType", supportsAllDrives=True)
            .execute()
        )
        print(f"{OK} Template acessivel: {meta_template.get('name')!r}")
        print(f"     ID: {config.id_apresentacao_modelo}")
    except Exception as e:
        if "404" in str(e):
            print(f"{ERRO} Template NAO acessivel (aguardando liberacao do Workspace admin).")
            print(f"     ID: {config.id_apresentacao_modelo}")
            print("     Apos liberacao, rode este script novamente para confirmar.")
        else:
            print(f"{ERRO} Erro ao acessar template: {e}")
    print()

    # ------------------------------------------------------------------
    # Resumo
    # ------------------------------------------------------------------
    print("=" * 60)
    print("  Para executar o pipeline completo:")
    print("  poetry run python -m status_report.main")
    print("  poetry run python -m status_report.main --force-run  (ignorar dia da semana)")
    print("=" * 60)


def _dia_semana(d: date) -> str:
    nomes = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]
    return nomes[d.weekday()]


if __name__ == "__main__":
    main()
