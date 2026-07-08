"""Inspeciona PROJ_CRON_ETAPA para entender previsto por cargo.

Uso:
    poetry run python scripts/inspecionar_etapas_cronograma.py [nr_seq_proj]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.repositorio_oracle import conectar

_SQL_ETAPAS = """
    SELECT
        d.nr_sequencia                                       AS seq_crono,
        d.ds_objetivo                                        AS objetivo,
        d.dt_inicio                                          AS crono_inicio,
        d.dt_fim                                             AS crono_fim,
        e.nr_sequencia                                       AS seq_etapa,
        e.ds_atividade                                       AS atividade,
        e.ie_fase                                            AS ie_fase,
        e.nr_seq_etapa                                       AS nr_seq_etapa,
        e.qt_hora_prev                                       AS qt_hora_prev,
        e.qt_hora_real                                       AS qt_hora_real,
        e.qt_hora_saldo                                      AS qt_hora_saldo,
        e.dt_inicio_prev                                     AS etapa_inicio,
        e.dt_fim_prev                                        AS etapa_fim,
        e.cd_funcao                                          AS cd_funcao,
        e.ie_papel_executor                                  AS ie_papel_executor,
        CASE
            WHEN upper(e.ds_atividade) LIKE '%MONITORAMENTO E CONTROLE%'
                 AND e.ie_fase = 'N' THEN 'COORDENADOR'
            WHEN e.nr_seq_etapa = 116 THEN 'COORDENADOR'
            WHEN upper(e.ds_atividade) LIKE '%ARQUI%'
                 AND e.ie_fase = 'N' THEN 'ARQUITETO'
            WHEN e.nr_seq_etapa = 115 THEN 'ARQUITETO'
            ELSE 'ANALISTA'
        END                                                  AS funcao
    FROM proj_cronograma d
    JOIN proj_projeto p ON d.nr_seq_proj = p.nr_sequencia
    JOIN proj_cron_etapa e ON d.nr_sequencia = e.nr_seq_cronograma
    WHERE p.nr_sequencia = :nr_seq_proj
    ORDER BY d.nr_sequencia, e.nr_sequencia
"""

_SQL_COLUNAS = """
    SELECT column_name, data_type
      FROM all_tab_columns
     WHERE owner = UPPER(:schema)
       AND table_name = 'PROJ_CRON_ETAPA'
     ORDER BY column_id
"""


def main() -> None:
    nr_seq_proj = int(sys.argv[1]) if len(sys.argv) > 1 else 2498
    config = carregar_configuracoes()

    print(f"Projeto #{nr_seq_proj}\n")

    with conectar(config) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                _SQL_COLUNAS, schema=(config.oracle_schema or "GHR").upper()
            )
            cols = cursor.fetchall()
            print("=" * 70)
            print("COLUNAS PROJ_CRON_ETAPA")
            print("=" * 70)
            for nome, tipo in cols:
                print(f"  {nome:30} {tipo}")

            cursor.execute(_SQL_ETAPAS, nr_seq_proj=nr_seq_proj)
            linhas = cursor.fetchall()

    print("\n" + "=" * 70)
    print("ETAPAS DO CRONOGRAMA")
    print("=" * 70)
    if not linhas:
        print("  (sem etapas)")
        return

    por_funcao: dict[str, float] = {}
    crono_atual = None
    for row in linhas:
        (
            seq_crono,
            objetivo,
            crono_ini,
            crono_fim,
            seq_etapa,
            atividade,
            ie_fase,
            nr_seq_etapa,
            prev,
            real,
            saldo,
            etapa_ini,
            etapa_fim,
            cd_funcao,
            ie_papel,
            funcao,
        ) = row
        if seq_crono != crono_atual:
            crono_atual = seq_crono
            ini = crono_ini.strftime("%d/%m/%Y") if crono_ini else "-"
            fim = crono_fim.strftime("%d/%m/%Y") if crono_fim else "-"
            print(f"\n--- Cronograma {seq_crono} ({objetivo}) {ini} .. {fim} ---")
        prev_f = float(prev or 0)
        por_funcao[funcao] = por_funcao.get(funcao, 0) + prev_f
        print(
            f"  etapa={seq_etapa} funcao={funcao:11} prev={prev_f:8.2f} "
            f"real={float(real or 0):8.2f} saldo={float(saldo or 0):8.2f}\n"
            f"    atividade={atividade!r} ie_fase={ie_fase} nr_seq_etapa={nr_seq_etapa}\n"
            f"    vigencia_etapa="
            f"{etapa_ini.strftime('%d/%m/%Y') if etapa_ini else '-'} .. "
            f"{etapa_fim.strftime('%d/%m/%Y') if etapa_fim else '-'}\n"
            f"    cd_funcao={cd_funcao} ie_papel={ie_papel!r}"
        )

    print("\n" + "=" * 70)
    print("SOMA QT_HORA_PREV POR FUNCAO")
    print("=" * 70)
    for funcao, total in sorted(por_funcao.items()):
        print(f"  {funcao:11} = {total:.2f}h")


if __name__ == "__main__":
    main()
