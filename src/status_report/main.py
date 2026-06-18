"""CLI da automacao diaria de Status Report."""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import date

from status_report.aplicacao.pipeline_diario import (
    construir_data_referencia,
    executar_pipeline_diario,
)
from status_report.configuracao import Configuracoes, carregar_configuracoes


def main() -> int:
    argumentos = _interpretar_argumentos()
    configuracoes = carregar_configuracoes()
    configuracoes.validar()

    data_referencia = (
        date.fromisoformat(argumentos.date)
        if argumentos.date
        else construir_data_referencia(configuracoes.fuso_horario)
    )

    if argumentos.dry_run:
        configuracoes = replace(configuracoes, modo_simulacao=True)

    resultados = executar_pipeline_diario(
        configuracoes=configuracoes,
        data_referencia=data_referencia,
        forcar_execucao=argumentos.force_run,
    )

    houve_erro = False
    for resultado in resultados:
        rotulo = "OK" if resultado.sucesso else "ERRO"
        print(f"[{rotulo}] {resultado.cliente} | {resultado.mensagem}")
        if resultado.url_pdf:
            print(f"      PDF: {resultado.url_pdf}")
        if not resultado.sucesso:
            houve_erro = True

    return 1 if houve_erro else 0


def _interpretar_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automacao diaria de Status Report.")
    parser.add_argument("--date", help="Data de referencia no formato AAAA-MM-DD.")
    parser.add_argument(
        "--force-run",
        action="store_true",
        help="Executa mesmo em fim de semana.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nao gera arquivos, apenas valida fila de clientes.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
