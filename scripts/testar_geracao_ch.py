"""Gera uma apresentacao completa de teste para validar Controle de Horas + PF.

Uso:
    poetry run python scripts/testar_geracao_ch.py <nr_seq_proj> [nr_seq_cliente] [id_completo]

Exemplo (Marillac):
    poetry run python scripts/testar_geracao_ch.py 2614 0 "ID:0026-26 - Atualiza Marillac"
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from status_report.aplicacao.pipeline_diario import _processar_cliente
from status_report.configuracao import carregar_configuracoes
from status_report.dominio.modelos import ClienteFila
from status_report.infraestrutura.autenticacao_google import construir_servicos_google


def _log(msg: str, tag: str = "info") -> None:
    print(f"[{tag}] {msg}")


def main() -> None:
    nr_seq_proj = sys.argv[1] if len(sys.argv) > 1 else "2614"
    nr_seq_cliente = sys.argv[2] if len(sys.argv) > 2 else "0"
    id_completo = sys.argv[3] if len(sys.argv) > 3 else "ID:0026-26 - Atualiza Marillac"

    config = carregar_configuracoes()
    servicos = construir_servicos_google(config)

    cliente = ClienteFila(
        nome_curto="TESTE Controle de Horas",
        cliente_id_completo=id_completo,
        coordenadora="Jordana",
        spreadsheet_origem_id="",
        nome_pdf_customizado="TESTE - Controle de Horas",
        nr_seq_cliente=nr_seq_cliente,
        nr_seq_proj=nr_seq_proj,
        nome_projeto=id_completo,
    )

    resultado = _processar_cliente(
        configuracoes=config,
        servicos=servicos,
        cliente=cliente,
        data_referencia=date.today(),
        log_fn=_log,
    )
    print("\n" + "=" * 60)
    print(f"Sucesso: {resultado.sucesso}")
    print(f"Mensagem: {resultado.mensagem}")
    print(f"Link: {resultado.url_pdf}")
    for caminho in resultado.caminhos_locais:
        print(f"Download: {caminho}")


if __name__ == "__main__":
    main()
