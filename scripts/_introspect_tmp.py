import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.repositorio_oracle import conectar

config = carregar_configuracoes()

TABELAS = ["PROJ_RAT", "PROJ_RAT_ATIV", "PROJ_CRON_ETAPA", "PROJ_CRONOGRAMA"]

with conectar(config) as con:
    cur = con.cursor()
    for t in TABELAS:
        print("=" * 70)
        print(t)
        print("=" * 70)
        cur.execute(
            "SELECT column_name, data_type FROM all_tab_columns "
            "WHERE owner='GHR' AND table_name=:t ORDER BY column_id",
            t=t,
        )
        for nome, tipo in cur.fetchall():
            print(f"  {nome:35} {tipo}")
        print()

    print("#" * 70)
    print("AMOSTRA proj_rat do projeto 2614")
    print("#" * 70)
    cur.execute("SELECT * FROM proj_rat WHERE nr_seq_proj = 2614")
    cols = [d[0] for d in cur.description]
    print(" | ".join(cols))
    for row in cur.fetchall()[:10]:
        print(" | ".join(str(v) for v in row))
