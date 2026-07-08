"""Testa a conexao com o Oracle e, opcionalmente, lista os projetos de um cliente.

Uso:
    poetry run python scripts/verificar_oracle.py              # so testa a conexao
    poetry run python scripts/verificar_oracle.py 12345        # lista projetos do cliente 12345
"""
from __future__ import annotations

import sys

from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.repositorio_oracle import (
    OracleNaoConfigurado,
    listar_projetos_ativos_do_cliente,
    testar_conexao,
)


def main() -> int:
    config = carregar_configuracoes()

    if not config.oracle_configurado():
        print("Oracle nao configurado. Preencha ORACLE_* no .env.")
        return 1

    print(f"Conectando em {config.oracle_dsn()} como {config.oracle_usuario}...")
    try:
        banner = testar_conexao(config)
    except OracleNaoConfigurado as e:
        print(f"[ERRO] {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha ao conectar: {e}")
        return 1

    print(f"[OK] Conexao estabelecida.\n     {banner}")

    if len(sys.argv) > 1:
        nr_seq_cliente = sys.argv[1]
        print(f"\nProjetos ativos do cliente {nr_seq_cliente}:")
        try:
            projetos = listar_projetos_ativos_do_cliente(config, nr_seq_cliente)
        except Exception as e:  # noqa: BLE001
            print(f"[ERRO] Falha na consulta: {e}")
            return 1
        if not projetos:
            print("  (nenhum projeto ativo encontrado)")
        for projeto in projetos:
            print(f"  #{projeto.nr_seq_proj}  {projeto.titulo}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
