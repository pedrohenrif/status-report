"""Agrega as consultas do Controle de Horas em dados prontos para o slide.



Monta a estrutura usada no relatorio manual das coordenadoras:



- cabecalho (cliente, projeto, vigencia, coordenador);

- resumo por funcao (contrato/consumo/saldo);

- serie mensal por funcao (previsto x executado x saldo);

- blocos por analista com todos os meses da vigencia.



O previsto por cargo vem da Consulta C (etapas ie_fase='N' do cronograma).

Quando a etapa cita o mes no titulo (ex.: 'Suporte analista - Abril 2026'),

usa esse mes; caso contrario rateia uniformemente pelos meses da vigencia.

"""

from __future__ import annotations



import re

from collections import defaultdict

from datetime import datetime



from status_report.dominio.modelos import (

    BlocoAnalistaHoras,

    ControleHoras,

    LinhaHorasPlanejado,

    LinhaHorasPrevistoEtapa,

    LinhaHorasRealizado,

    LinhaMensalHoras,

)



_FUNCAO_COORDENADOR = "COORDENADOR"

_FUNCAO_ANALISTA = "ANALISTA"

_FUNCOES_PRINCIPAIS = ("COORDENADOR", "ARQUITETO", "ANALISTA")

_CARGA_MENSAL_ANALISTA = 160.0



_REGEX_MES_ANO = re.compile(

    r"(janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|"

    r"setembro|outubro|novembro|dezembro)\s*[\-/]?\s*(\d{4})",

    re.IGNORECASE,

)

_MAP_MES_NOME = {

    "janeiro": 1,

    "fevereiro": 2,

    "março": 3,

    "marco": 3,

    "abril": 4,

    "maio": 5,

    "junho": 6,

    "julho": 7,

    "agosto": 8,

    "setembro": 9,

    "outubro": 10,

    "novembro": 11,

    "dezembro": 12,

}





def _meses_entre(inicio: datetime | None, fim: datetime | None) -> list[str]:

    """Lista de meses 'MM/YYYY' entre inicio e fim (inclusive)."""

    if inicio is None or fim is None:

        return []

    ano, mes = inicio.year, inicio.month

    resultado: list[str] = []

    while (ano, mes) <= (fim.year, fim.month):

        resultado.append(f"{mes:02d}/{ano}")

        mes += 1

        if mes > 12:

            mes = 1

            ano += 1

    return resultado





def _ordenar_mes(mes: str) -> tuple[int, int]:

    """Chave de ordenacao para 'MM/YYYY'."""

    try:

        mm, yyyy = mes.split("/")

        return (int(yyyy), int(mm))

    except (ValueError, AttributeError):

        return (0, 0)





def _cronograma_inativo(objetivo: str) -> bool:

    """Cronogramas marcados para inativar nao entram na vigencia do contrato."""

    return "inativar" in (objetivo or "").lower()





def _seqs_cronogramas_vigencia(

    planejado: list[LinhaHorasPlanejado],

    realizado: list[LinhaHorasRealizado],

) -> set[int]:

    """Seleciona cronogramas que definem a vigencia exibida nas tabelas."""

    com_realizado = {

        p.seq_crono for p in planejado if p.horas_realizado_total > 0

    }

    com_realizado |= {

        r.seq_crono for r in realizado if r.horas_trabalhadas > 0

    }



    candidatos = [p for p in planejado if not _cronograma_inativo(p.objetivo_cronograma)]

    if not candidatos:

        candidatos = list(planejado)



    if com_realizado:

        ativos = [p for p in candidatos if p.seq_crono in com_realizado]

        if ativos:

            return {p.seq_crono for p in ativos}



    return {p.seq_crono for p in candidatos}





def _funcao_do_cronograma(objetivo: str) -> str | None:

    """Tenta mapear um cronograma a um papel quando o objetivo indica isso."""

    texto = (objetivo or "").lower()

    if "coord" in texto or "monitoramento" in texto:

        return _FUNCAO_COORDENADOR

    if "arqui" in texto:

        return "ARQUITETO"

    if "anal" in texto:

        return _FUNCAO_ANALISTA

    return None





def _mes_da_atividade(texto: str) -> str | None:

    """Extrai MM/YYYY do titulo da etapa quando houver mes por extenso."""

    match = _REGEX_MES_ANO.search(texto or "")

    if not match:

        return None

    nome = match.group(1).lower().replace("ç", "c")

    if nome not in _MAP_MES_NOME:

        return None

    mes = _MAP_MES_NOME[nome]

    ano = int(match.group(2))

    return f"{mes:02d}/{ano}"





def _previsto_por_funcao_e_mes_cronograma(

    planejado: list[LinhaHorasPlanejado],

) -> tuple[dict[str, float], dict[str, dict[str, float]]]:

    """Fallback: previsto por funcao a partir do objetivo do cronograma."""

    totais: dict[str, float] = defaultdict(float)

    mensal: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))



    for p in planejado:

        funcao = _funcao_do_cronograma(p.objetivo_cronograma)

        if funcao is None:

            continue

        totais[funcao] += p.horas_previstas_total

        for mes in _meses_entre(p.dt_inicio, p.dt_fim):

            mensal[funcao][mes] += p.horas_previstas_mes



    return (

        {k: round(v, 2) for k, v in totais.items()},

        {k: dict(v) for k, v in mensal.items()},

    )





def _previsto_por_funcao_e_mes_etapas(

    etapas: list[LinhaHorasPrevistoEtapa],

    seqs_cronograma: set[int],

    meses_vigencia: list[str],

) -> tuple[dict[str, float], dict[str, dict[str, float]]]:

    """Agrega previsto por cargo/mes a partir das etapas do cronograma."""

    totais: dict[str, float] = defaultdict(float)

    mensal: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    sem_mes: dict[tuple[int, str], float] = defaultdict(float)

    meses_crono: dict[int, list[str]] = {}



    for etapa in etapas:

        if etapa.seq_crono not in seqs_cronograma:

            continue

        horas = etapa.horas_previstas

        if horas <= 0:

            continue



        totais[etapa.funcao] += horas

        mes = _mes_da_atividade(etapa.ds_atividade)

        if mes:

            mensal[etapa.funcao][mes] += horas

            continue



        sem_mes[(etapa.seq_crono, etapa.funcao)] += horas

        if etapa.seq_crono not in meses_crono:

            meses_crono[etapa.seq_crono] = _meses_entre(

                etapa.crono_inicio, etapa.crono_fim

            )



    for (seq_crono, funcao), horas in sem_mes.items():

        meses = meses_vigencia or meses_crono.get(seq_crono, [])

        if not meses:

            continue

        por_mes = horas / len(meses)

        for mes in meses:

            mensal[funcao][mes] += por_mes



    return (

        {k: round(v, 2) for k, v in totais.items()},

        {

            funcao: {mes: round(valor, 2) for mes, valor in por_mes.items()}

            for funcao, por_mes in mensal.items()

        },

    )





def _previsto_mes_projeto(

    previsto_funcao_mes: dict[str, dict[str, float]],

) -> dict[str, float]:

    resultado: dict[str, float] = defaultdict(float)

    for por_mes in previsto_funcao_mes.values():

        for mes, horas in por_mes.items():

            resultado[mes] += horas

    return {k: round(v, 2) for k, v in resultado.items()}





def _distribuir_previsto_analistas(

    meses_vigencia: list[str],

    previsto_analista_mes: dict[str, float],

    realizado: list[LinhaHorasRealizado],

    chaves: list[tuple[int, str, str]],

) -> dict[tuple[int, str, str], dict[str, float]]:

    """Reparte o previsto mensal de analista entre as pessoas do projeto."""

    analistas = [c for c in chaves if c[2] == _FUNCAO_ANALISTA]

    resultado: dict[tuple[int, str, str], dict[str, float]] = defaultdict(dict)



    for mes in meses_vigencia:

        previsto = previsto_analista_mes.get(mes, 0.0)

        if previsto <= 0:

            continue



        ativos = [

            chave

            for chave in analistas

            if any(

                r.mes == mes

                and r.cd_executor == chave[0]

                and r.horas_trabalhadas > 0

                for r in realizado

            )

        ]
        if not ativos:
            continue

        valor = min(_CARGA_MENSAL_ANALISTA, round(previsto / len(ativos), 2))

        for chave in ativos:

            resultado[chave][mes] = valor



    return resultado





def _serie_mensal(

    meses_vigencia: list[str],

    previsto_mes: dict[str, float],

    executado_mes: dict[str, float],

) -> list[LinhaMensalHoras]:

    return [

        LinhaMensalHoras(

            mes=m,

            previsto=round(previsto_mes.get(m, 0.0), 2),

            executado=round(executado_mes.get(m, 0.0), 2),

        )

        for m in meses_vigencia

    ]





def montar_controle_horas(

    planejado: list[LinhaHorasPlanejado],

    realizado: list[LinhaHorasRealizado],

    previsto_etapas: list[LinhaHorasPrevistoEtapa] | None = None,

) -> ControleHoras | None:

    """Cruza Planejado + Realizado + Previsto/Etapas em ControleHoras."""

    if not planejado and not realizado:

        return None



    ref = planejado[0] if planejado else None

    nome_cliente = ref.nome_cliente if ref else ""

    nome_projeto = ref.nome_projeto if ref else ""

    nr_seq_proj = ref.nr_seq_proj if ref else (realizado[0].nr_seq_proj if realizado else 0)



    seqs_vigencia = _seqs_cronogramas_vigencia(planejado, realizado)

    planejado_vigencia = [p for p in planejado if p.seq_crono in seqs_vigencia]



    inicios = [p.dt_inicio for p in planejado_vigencia if p.dt_inicio]

    fins = [p.dt_fim for p in planejado_vigencia if p.dt_fim]

    vigencia_inicio = min(inicios) if inicios else None

    vigencia_fim = max(fins) if fins else None



    realizado_total = round(sum(r.horas_trabalhadas for r in realizado), 2)



    coordenadores = sorted(

        {r.analista for r in realizado if r.funcao == _FUNCAO_COORDENADOR}

    )

    coordenador = ", ".join(coordenadores)



    realizado_por_funcao: dict[str, float] = defaultdict(float)

    executado_funcao_mes: dict[str, dict[str, float]] = defaultdict(

        lambda: defaultdict(float)

    )

    for r in realizado:

        realizado_por_funcao[r.funcao] += r.horas_trabalhadas

        executado_funcao_mes[r.funcao][r.mes] += r.horas_trabalhadas

    realizado_por_funcao = {k: round(v, 2) for k, v in realizado_por_funcao.items()}



    meses_vigencia = _meses_entre(vigencia_inicio, vigencia_fim)



    if previsto_etapas:

        previsto_por_funcao, previsto_funcao_mes = _previsto_por_funcao_e_mes_etapas(

            previsto_etapas, seqs_vigencia, meses_vigencia

        )

    else:

        previsto_por_funcao, previsto_funcao_mes = _previsto_por_funcao_e_mes_cronograma(

            planejado_vigencia

        )



    previsto_mes_projeto = _previsto_mes_projeto(previsto_funcao_mes)

    if previsto_por_funcao:

        previsto_total = round(sum(previsto_por_funcao.values()), 2)

    else:

        previsto_total = round(

            sum(p.horas_previstas_total for p in planejado_vigencia), 2

        )



    executado_mes_projeto: dict[str, float] = defaultdict(float)

    for r in realizado:

        executado_mes_projeto[r.mes] += r.horas_trabalhadas



    if not meses_vigencia:

        meses_vigencia = sorted(

            set(previsto_mes_projeto) | set(executado_mes_projeto), key=_ordenar_mes

        )



    meses = _serie_mensal(meses_vigencia, previsto_mes_projeto, executado_mes_projeto)



    mensal_por_funcao: dict[str, list[LinhaMensalHoras]] = {}

    funcoes = sorted(

        set(realizado_por_funcao) | set(previsto_por_funcao),

        key=lambda f: _FUNCOES_PRINCIPAIS.index(f) if f in _FUNCOES_PRINCIPAIS else 9,

    )

    for funcao in funcoes:

        mensal_por_funcao[funcao] = _serie_mensal(

            meses_vigencia,

            previsto_funcao_mes.get(funcao, {}),

            executado_funcao_mes.get(funcao, {}),

        )



    analistas = _montar_analistas(

        realizado,

        meses_vigencia,

        previsto_funcao_mes.get(_FUNCAO_ANALISTA, {}),

    )



    return ControleHoras(

        nome_cliente=nome_cliente,

        nr_seq_proj=nr_seq_proj,

        nome_projeto=nome_projeto,

        coordenador=coordenador,

        vigencia_inicio=vigencia_inicio,

        vigencia_fim=vigencia_fim,

        previsto_total=previsto_total,

        realizado_total=realizado_total,

        realizado_por_funcao=realizado_por_funcao,

        previsto_por_funcao=previsto_por_funcao,

        meses=meses,

        meses_vigencia=meses_vigencia,

        mensal_por_funcao=mensal_por_funcao,

        analistas=analistas,

    )





def _montar_analistas(

    realizado: list[LinhaHorasRealizado],

    meses_vigencia: list[str],

    previsto_analista_mes: dict[str, float],

) -> list[BlocoAnalistaHoras]:

    """Agrupa o realizado por pessoa, com previsto mensal quando disponivel."""

    chaves: dict[tuple[int, str, str], dict[str, float]] = defaultdict(

        lambda: defaultdict(float)

    )

    for r in realizado:

        chaves[(r.cd_executor, r.analista, r.funcao)][r.mes] += r.horas_trabalhadas



    previsto_por_pessoa = _distribuir_previsto_analistas(

        meses_vigencia,

        previsto_analista_mes,

        realizado,

        list(chaves.keys()),

    )



    blocos: list[BlocoAnalistaHoras] = []

    for (cd_executor, analista, funcao), por_mes in chaves.items():

        previsto_mes = previsto_por_pessoa.get((cd_executor, analista, funcao), {})

        meses = [

            LinhaMensalHoras(

                mes=m,

                previsto=round(previsto_mes.get(m, 0.0), 2),

                executado=round(por_mes.get(m, 0.0), 2),

            )

            for m in meses_vigencia

        ]

        blocos.append(

            BlocoAnalistaHoras(

                analista=analista,

                funcao=funcao,

                cd_executor=cd_executor,

                meses=meses,

                total_executado=round(sum(por_mes.values()), 2),

            )

        )

    blocos.sort(key=lambda b: (b.funcao, b.analista))

    return blocos

