"""Testa as consultas do Controle de Horas contra um projeto/cliente real.

Uso:
    poetry run python scripts/testar_controle_horas.py <nr_seq_cliente> [nr_seq_proj]

Passe 0 para ignorar um filtro. Exemplo (todos os projetos do cliente 72):
    poetry run python scripts/testar_controle_horas.py 72 0
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:  # acentos no console do Windows
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from status_report.aplicacao.agregacao_controle_horas import montar_controle_horas
from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.repositorio_oracle import (
    consultar_horas_planejado,
    consultar_horas_previsto_etapas,
    consultar_horas_realizado,
)


def main() -> None:
    nr_seq_cliente = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    nr_seq_proj = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    config = carregar_configuracoes()

    print(f"Filtros: nr_seq_cliente={nr_seq_cliente} nr_seq_proj={nr_seq_proj}\n")

    print("=" * 70)
    print("CONSULTA A - PLANEJADO (por cronograma)")
    print("=" * 70)
    planejado = consultar_horas_planejado(config, nr_seq_cliente, nr_seq_proj)
    for p in planejado:
        ini = p.dt_inicio.strftime("%d/%m/%Y") if p.dt_inicio else "-"
        fim = p.dt_fim.strftime("%d/%m/%Y") if p.dt_fim else "-"
        print(
            f"  crono={p.seq_crono} proj={p.nr_seq_proj} '{p.nome_projeto}'\n"
            f"    objetivo={p.objetivo_cronograma!r}\n"
            f"    vigencia={ini}..{fim} meses={p.qt_meses}\n"
            f"    prev_total={p.horas_previstas_total} real_total={p.horas_realizado_total} "
            f"prev_mes={p.horas_previstas_mes}"
        )
    print(f"\n  Total de cronogramas: {len(planejado)}")
    print(f"  Cliente: {planejado[0].nome_cliente if planejado else '-'}")

    print("\n" + "=" * 70)
    print("CONSULTA B - REALIZADO (por analista/funcao/mes)")
    print("=" * 70)
    realizado = consultar_horas_realizado(config, nr_seq_cliente, nr_seq_proj)
    for r in realizado:
        print(
            f"  crono={r.seq_crono} {r.mes} [{r.funcao:11}] "
            f"{r.analista} (cd={r.cd_executor}) = {r.horas_trabalhadas}h"
        )
    print(f"\n  Total de linhas realizadas: {len(realizado)}")

    print("\n" + "=" * 70)
    print("CONSULTA C - PREVISTO (por etapa/cargo, ie_fase=N)")
    print("=" * 70)
    previsto_etapas = consultar_horas_previsto_etapas(
        config, nr_seq_cliente, nr_seq_proj
    )
    por_funcao_prev = defaultdict(float)
    for e in previsto_etapas:
        por_funcao_prev[e.funcao] += e.horas_previstas
    print(f"  Total de etapas: {len(previsto_etapas)}")
    for funcao, horas in sorted(por_funcao_prev.items()):
        print(f"    {funcao:11} = {round(horas, 2)}h")
    for e in previsto_etapas[:8]:
        print(
            f"  crono={e.seq_crono} [{e.funcao:11}] prev={e.horas_previstas} "
            f"| {e.ds_atividade[:60]}"
        )
    if len(previsto_etapas) > 8:
        print(f"  ... (+{len(previsto_etapas) - 8} etapas)")

    print("\n" + "-" * 70)
    print("AGREGACOES (para validar premissas)")
    print("-" * 70)

    por_funcao = defaultdict(float)
    por_analista = defaultdict(float)
    for r in realizado:
        por_funcao[r.funcao] += r.horas_trabalhadas
        por_analista[(r.funcao, r.analista)] += r.horas_trabalhadas

    print("\n  Realizado por FUNCAO:")
    for funcao, horas in sorted(por_funcao.items()):
        print(f"    {funcao:11} = {round(horas, 2)}h")

    print("\n  Realizado por ANALISTA:")
    for (funcao, analista), horas in sorted(por_analista.items()):
        print(f"    [{funcao:11}] {analista} = {round(horas, 2)}h")

    print("\n  Cronograma -> funcoes que aparecem (checar se 1 crono = 1 papel):")
    cronos = defaultdict(set)
    for r in realizado:
        cronos[r.seq_crono].add(r.funcao)
    for crono, funcoes in sorted(cronos.items()):
        print(f"    crono {crono}: {sorted(funcoes)}")

    total_prev = sum(p.horas_previstas_total for p in planejado)
    total_real_a = sum(p.horas_realizado_total for p in planejado)
    total_real_b = sum(r.horas_trabalhadas for r in realizado)
    print("\n  Totais:")
    print(f"    Previsto (A) = {round(total_prev, 2)}h")
    print(f"    Realizado (A, qt_horas_realizado) = {round(total_real_a, 2)}h")
    print(f"    Realizado (B, soma rat)           = {round(total_real_b, 2)}h")

    _imprimir_proposta(planejado, realizado, previsto_etapas)


def _imprimir_proposta(planejado, realizado, previsto_etapas) -> None:
    print("\n" + "#" * 70)
    print("PROPOSTA DE SLIDE (agregacao) - Consulta C + Realizado")
    print("#" * 70)
    ch = montar_controle_horas(planejado, realizado, previsto_etapas)
    if ch is None:
        print("  (sem dados)")
        return

    ini = ch.vigencia_inicio.strftime("%d/%m/%Y") if ch.vigencia_inicio else "-"
    fim = ch.vigencia_fim.strftime("%d/%m/%Y") if ch.vigencia_fim else "-"
    print("\n[CABECALHO]")
    print(f"  Cliente    : {ch.nome_cliente}")
    print(f"  Projeto    : {ch.nome_projeto} (#{ch.nr_seq_proj})")
    print(f"  Vigencia   : {ini} .. {fim}")
    print(f"  Coordenador: {ch.coordenador or '(nao ha funcao COORDENADOR)'}")
    print(f"  Previsto   : {ch.previsto_total}h")
    print(f"  Realizado  : {ch.realizado_total}h")
    print(f"  Saldo      : {ch.saldo_total}h")

    print("\n[REALIZADO POR FUNCAO]")
    for funcao, horas in sorted(ch.realizado_por_funcao.items()):
        print(f"  {funcao:12} = {horas}h")

    print("\n[PREVISTO POR FUNCAO]")
    for funcao, horas in sorted(ch.previsto_por_funcao.items()):
        print(f"  {funcao:12} = {horas}h")

    print("\n[MENSAL POR FUNCAO - amostra ANALISTA]")
    for m in ch.mensal_por_funcao.get("ANALISTA", [])[:6]:
        print(f"  {m.mes:9} prev={m.previsto:>8} exec={m.executado:>8}")

    print("\n[SERIE MENSAL - Previsto x Executado x Saldo]")
    print(f"  {'Mes':9} {'Previsto':>10} {'Executado':>10} {'Saldo':>10}")
    for m in ch.meses:
        print(f"  {m.mes:9} {m.previsto:>10} {m.executado:>10} {m.saldo:>10}")

    print("\n[SLIDE ANALISTAS - blocos por pessoa]")
    for b in ch.analistas:
        print(f"\n  {b.analista} [{b.funcao}] - total {b.total_executado}h")
        for m in b.meses:
            if m.previsto or m.executado:
                print(
                    f"      {m.mes:9} previsto={m.previsto} executado={m.executado}"
                )


if __name__ == "__main__":
    main()
