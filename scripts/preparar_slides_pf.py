"""Prepara os slides 6/7/8 do template para Projeto Funcional dinamico.

Cria uma COPIA do template, remove imagens e tabelas antigas dos slides de
Projeto Funcional (mantem apenas o titulo) e insere tabelas de exemplo.

Use a copia gerada para ajustar largura/posicao no Google Slides. Depois de
satisfeito, substitua o template base (GOOGLE_TEMPLATE_PRESENTATION_ID no .env)
por essa versao limpa.

Uso:
    poetry run python scripts/preparar_slides_pf.py
    poetry run python scripts/preparar_slides_pf.py --somente-limpar
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from status_report.aplicacao.render_projeto_funcional import (
    preparar_slides_projeto_funcional,
)
from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.autenticacao_google import construir_servicos_google
from status_report.infraestrutura.repositorio_drive import (
    copiar_apresentacao,
    criar_ou_obter_subpasta,
    obter_link_arquivo,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Limpa slides 6/7/8 e insere tabelas de exemplo para ajuste manual."
    )
    parser.add_argument(
        "--somente-limpar",
        action="store_true",
        help="Remove conteudo antigo sem inserir tabelas de exemplo.",
    )
    args = parser.parse_args()

    config = carregar_configuracoes()
    servicos = construir_servicos_google(config)
    hoje = date.today()

    print("Copiando template...")
    id_subpasta = criar_ou_obter_subpasta(
        drive=servicos.drive,
        id_pasta_pai=config.id_pasta_saida,
        nome="PREPARAR_TEMPLATE",
    )
    id_copia = copiar_apresentacao(
        drive=servicos.drive,
        id_modelo=config.id_apresentacao_modelo,
        nome_da_copia=f"PREPARAR_PF - {hoje.isoformat()}",
        id_pasta_destino=id_subpasta,
    )

    if args.somente_limpar:
        print("Limpando slides 6/7/8 (sem tabelas de exemplo)...")
    else:
        print("Limpando slides 6/7/8 e inserindo tabelas de exemplo...")

    preparar_slides_projeto_funcional(
        slides=servicos.slides,
        presentation_id=id_copia,
        incluir_tabela_exemplo=not args.somente_limpar,
    )

    link = obter_link_arquivo(drive=servicos.drive, id_arquivo=id_copia)
    print("\nPronto! Abra a copia e ajuste o layout das tabelas:")
    print(f"  {link}")
    print("\nProximos passos:")
    print("  1. Ajuste largura/posicao das tabelas nos slides 6, 7 e 8.")
    print("  2. Confirme que os titulos usam {{QTD_CONCLUIDOS}}, etc.")
    print("  3. Copie o ID desta apresentacao para GOOGLE_TEMPLATE_PRESENTATION_ID.")
    print("\nNota: o pipeline continua recriando as tabelas a cada geracao.")
    print("Este script serve para limpar o template base e validar o layout.")


if __name__ == "__main__":
    main()
