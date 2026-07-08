"""Renderiza os slides do Controle de Horas no layout do relatorio manual.

Slide principal ({{MODELO_CONTROLE_HORAS}}):
- cabecalho do projeto;
- resumo Contrato/Consumo/Saldo por funcao;
- tabelas mensais de Coordenacao e Arquiteto (Previsto/Executado/Saldo).

Slide(s) de analistas ({{MODELO_CONTROLE_HORAS_ANALISTAS}}):
- ate 3 mini-tabelas por slide, uma por analista, com meses da vigencia.
"""
from __future__ import annotations

from datetime import date

from status_report.aplicacao.agregacao_controle_horas import _ordenar_mes
from status_report.dominio.modelos import BlocoAnalistaHoras, ControleHoras, LinhaMensalHoras
from status_report.infraestrutura.repositorio_tabela_slide import (
    COR_CABECALHO,
    LayoutTabela,
    PlantaTabela,
    requests_conteudo,
    requests_estrutura,
)

_FUNCAO_COORDENADOR = "COORDENADOR"
_FUNCAO_ARQUITETO = "ARQUITETO"
_FUNCAO_ANALISTA = "ANALISTA"
_ORDEM_FUNCAO = {_FUNCAO_COORDENADOR: 0, _FUNCAO_ARQUITETO: 1, _FUNCAO_ANALISTA: 2}
_MARGEM = 0.35
_GAP = 0.15
_Y_TOPO_PADRAO = 1.55
_MARGEM_APOS_TITULO = 0.12
_TITULO = "controle de horas"
_POL = 914400
_MAX_ANALISTAS_POR_SLIDE = 3

_MESES_PT = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)


def _fmt_saldo(previsto: float, executado: float) -> str:
    """Saldo = previsto - executado (negativo quando estourou o previsto)."""
    return _fmt(round(previsto - executado, 2))


def _fmt(valor: float | None, vazio_se_zero: bool = False) -> str:
    if valor is None:
        return ""
    n = round(float(valor), 2)
    if vazio_se_zero and n == 0:
        return ""
    if n == int(n):
        return str(int(n))
    return f"{n:.2f}".replace(".", ",")


def _data(dt) -> str:
    return dt.strftime("%d/%m/%Y") if dt else "-"


def _meses_incluem_ano(meses: list[str]) -> bool:
    anos: set[int] = set()
    for mes in meses:
        try:
            _, yyyy = mes.split("/")
            anos.add(int(yyyy))
        except ValueError:
            continue
    return len(anos) > 1


def _rotulo_mes(mes: str, incluir_ano: bool = False) -> str:
    try:
        mm, yyyy = mes.split("/")
        nome = _MESES_PT[int(mm) - 1]
        return f"{nome}/{yyyy[-2:]}" if incluir_ano else nome
    except (ValueError, IndexError):
        return mes


def _mes_lte_referencia(mes: str, referencia: date) -> bool:
    try:
        mm, yyyy = mes.split("/")
        return (int(yyyy), int(mm)) <= (referencia.year, referencia.month)
    except ValueError:
        return False


def _totais_periodo(
    linhas: list[LinhaMensalHoras], referencia: date, ate_referencia: bool
) -> tuple[float, float, float]:
    selecionadas = [
        l
        for l in linhas
        if not ate_referencia or _mes_lte_referencia(l.mes, referencia)
    ]
    previsto = round(sum(l.previsto for l in selecionadas), 2)
    executado = round(sum(l.executado for l in selecionadas), 2)
    return previsto, executado, round(previsto - executado, 2)


def _page_size(slides, presentation_id: str) -> tuple[float, float]:
    apresentacao = (
        slides.presentations()
        .get(presentationId=presentation_id, fields="pageSize")
        .execute()
    )
    ps = apresentacao.get("pageSize", {})
    largura = ps.get("width", {}).get("magnitude", 9144000) / 914400
    altura = ps.get("height", {}).get("magnitude", 5143500) / 914400
    return largura, altura


def _texto_elemento(elemento: dict) -> str:
    shape = elemento.get("shape")
    if not shape:
        return ""
    partes = [
        b.get("textRun", {}).get("content", "")
        for b in shape.get("text", {}).get("textElements", [])
    ]
    return "".join(partes)


def _fundo_polegadas(elemento: dict) -> float:
    transform = elemento.get("transform", {})
    tamanho = elemento.get("size", {})
    ty = transform.get("translateY", 0)
    altura = tamanho.get("height", {}).get("magnitude", 0)
    sy = transform.get("scaleY", 1) or 1
    return (ty + altura * sy) / _POL


def _analisar_slides(
    slides, presentation_id: str, slide_ids: set[str]
) -> dict[str, dict]:
    apresentacao = (
        slides.presentations()
        .get(
            presentationId=presentation_id,
            fields=(
                "slides(objectId,pageElements(objectId,transform,size,"
                "shape(text(textElements(textRun(content))))))"
            ),
        )
        .execute()
    )
    mapa: dict[str, dict] = {}
    for slide in apresentacao.get("slides", []):
        if slide["objectId"] not in slide_ids:
            continue
        remover: list[str] = []
        fundos_titulo: list[float] = []
        for el in slide.get("pageElements", []):
            if "elementGroup" in el:
                remover.append(el["objectId"])
                continue
            eh_titulo = _TITULO in _texto_elemento(el).strip().lower()
            if eh_titulo:
                fundos_titulo.append(_fundo_polegadas(el))
            else:
                remover.append(el["objectId"])
        y_topo = (
            max(fundos_titulo) + _MARGEM_APOS_TITULO
            if fundos_titulo
            else _Y_TOPO_PADRAO
        )
        mapa[slide["objectId"]] = {"remover": remover, "y_topo": max(y_topo, 1.2)}
    return mapa


def _limpar_elementos(
    slides, presentation_id: str, slide_ids: set[str], analise: dict[str, dict]
) -> None:
    """Remove conteudo antigo do slide-modelo (textos/tabelas), mantendo so o titulo."""
    apresentacao = (
        slides.presentations()
        .get(
            presentationId=presentation_id,
            fields="slides(objectId,pageElements(objectId))",
        )
        .execute()
    )
    existentes: set[str] = set()
    for slide in apresentacao.get("slides", []):
        if slide["objectId"] not in slide_ids:
            continue
        for el in slide.get("pageElements", []):
            existentes.add(el["objectId"])

    vistos: set[str] = set()
    requisicoes: list[dict] = []
    for info in analise.values():
        for oid in info["remover"]:
            if oid in existentes and oid not in vistos:
                vistos.add(oid)
                requisicoes.append({"deleteObject": {"objectId": oid}})
    _executar(slides, presentation_id, requisicoes)


def _altura_estimada(n_linhas_dados: int) -> float:
    return 0.28 + max(n_linhas_dados, 1) * 0.22


def renderizar_controle_horas(
    slides,
    presentation_id: str,
    slide_principal_id: str,
    slide_analistas_ids: list[str] | None,
    ch: ControleHoras,
    data_referencia: date | None = None,
) -> list[str]:
    """Preenche os slides do Controle de Horas. Retorna slide_ids a remover."""
    referencia = data_referencia or date.today()
    largura_slide, altura_slide = _page_size(slides, presentation_id)
    incluir_ano_mes = _meses_incluem_ano(ch.meses_vigencia)
    alvos = {slide_principal_id}
    if slide_analistas_ids:
        alvos.update(slide_analistas_ids)
    analise = _analisar_slides(slides, presentation_id, alvos)
    _limpar_elementos(slides, presentation_id, alvos, analise)
    info_principal = analise.get(
        slide_principal_id, {"remover": [], "y_topo": _Y_TOPO_PADRAO}
    )

    plantas: list[PlantaTabela] = []
    plantas.extend(
        _plantas_principal(
            ch,
            slide_principal_id,
            largura_slide,
            altura_slide,
            info_principal["remover"],
            info_principal["y_topo"],
            referencia,
            incluir_ano_mes,
        )
    )

    slides_para_remover: list[str] = []
    analistas = [b for b in ch.analistas if b.funcao == _FUNCAO_ANALISTA]
    ids_analistas = slide_analistas_ids or []

    if ids_analistas:
        if analistas:
            lotes = [
                analistas[i : i + _MAX_ANALISTAS_POR_SLIDE]
                for i in range(0, len(analistas), _MAX_ANALISTAS_POR_SLIDE)
            ]
            for indice_lote, lote in enumerate(lotes):
                if indice_lote >= len(ids_analistas):
                    break
                slide_id = ids_analistas[indice_lote]
                info = analise.get(slide_id, {"remover": [], "y_topo": _Y_TOPO_PADRAO})
                plantas.extend(
                    _plantas_analistas(
                        lote,
                        slide_id,
                        largura_slide,
                        altura_slide,
                        info["remover"],
                        info["y_topo"],
                        referencia,
                        indice_lote * _MAX_ANALISTAS_POR_SLIDE,
                        incluir_ano_mes,
                    )
                )
            slides_para_remover.extend(ids_analistas[len(lotes) :])
        else:
            slides_para_remover.extend(ids_analistas)

    _executar_plantas(slides, presentation_id, plantas)
    return slides_para_remover


def _plantas_principal(
    ch: ControleHoras,
    slide_id: str,
    largura_slide: float,
    altura_slide: float,
    remover: list[str],
    y_topo: float,
    referencia: date,
    incluir_ano_mes: bool,
) -> list[PlantaTabela]:
    largura_esq = 4.15
    x_esq = _MARGEM
    x_dir = _MARGEM + largura_esq + _GAP
    largura_dir = largura_slide - x_dir - _MARGEM

    info_linhas = [
        ["Cliente", ch.nome_cliente],
        ["ID", ch.nome_projeto],
        ["Vigência", f"{_data(ch.vigencia_inicio)} a {_data(ch.vigencia_fim)}"],
        ["Coordenador", ch.coordenador or "-"],
    ]
    info = PlantaTabela(
        table_object_id="tbl_ch_info",
        slide_object_id=slide_id,
        cabecalhos=["Campo", "Valor"],
        linhas=info_linhas,
        larguras_polegadas=[1.1, largura_esq - 1.1],
        cor_status=COR_CABECALHO,
        layout=LayoutTabela(
            x_polegadas=x_esq,
            y_polegadas=y_topo,
            largura_polegadas=largura_esq,
            altura_slide_polegadas=altura_slide,
        ),
    )

    y = y_topo + _altura_estimada(len(info_linhas)) + 0.12
    alocacao = _planta_alocacao(ch, slide_id, x_esq, y, largura_esq, altura_slide)
    y += _altura_estimada(len(alocacao.linhas)) + 0.12
    saldo_atual = _planta_resumo(
        ch, slide_id, x_esq, y, largura_esq, altura_slide, "Saldo Atual", referencia, True
    )
    y += _altura_estimada(len(saldo_atual.linhas)) + 0.1
    saldo_projeto = _planta_resumo(
        ch, slide_id, x_esq, y, largura_esq, altura_slide, "Saldo Contrato", referencia, False
    )

    metade = (largura_dir - _GAP) / 2
    mensais: list[PlantaTabela] = []
    for indice, funcao in enumerate((_FUNCAO_COORDENADOR, _FUNCAO_ARQUITETO)):
        linhas_mes = ch.mensal_por_funcao.get(funcao, [])
        if not linhas_mes and funcao not in ch.realizado_por_funcao:
            continue
        rotulo = "Coordenação" if funcao == _FUNCAO_COORDENADOR else "Arquiteto"
        mensais.append(
            _planta_mensal_funcao(
                rotulo,
                linhas_mes,
                slide_id,
                x_dir + indice * (metade + _GAP),
                y_topo,
                metade,
                altura_slide,
                referencia,
                f"tbl_ch_{funcao.lower()}",
                incluir_ano_mes,
            )
        )

    return [info, alocacao, saldo_atual, saldo_projeto, *mensais]


def _planta_alocacao(
    ch: ControleHoras,
    slide_id: str,
    x: float,
    y: float,
    largura: float,
    altura_slide: float,
) -> PlantaTabela:
    linhas: list[list[str]] = []
    for funcao in (_FUNCAO_COORDENADOR, _FUNCAO_ARQUITETO, _FUNCAO_ANALISTA):
        if funcao not in ch.realizado_por_funcao and funcao not in ch.previsto_por_funcao:
            continue
        rotulo = {
            _FUNCAO_COORDENADOR: "Horas Coordenação",
            _FUNCAO_ARQUITETO: "Horas Arquiteto",
            _FUNCAO_ANALISTA: "Horas Analista",
        }[funcao]
        prev_mes = 0.0
        if ch.mensal_por_funcao.get(funcao):
            com_previsto = [m for m in ch.mensal_por_funcao[funcao] if m.previsto]
            if com_previsto:
                prev_mes = com_previsto[0].previsto
        linhas.append(
            [
                rotulo,
                _fmt(prev_mes, vazio_se_zero=True),
                _fmt(ch.realizado_por_funcao.get(funcao, 0.0)),
                _fmt(ch.previsto_por_funcao.get(funcao, 0.0), vazio_se_zero=True),
            ]
        )

    if not linhas:
        linhas.append(["Horas Projeto", _fmt(ch.previsto_total / max(len(ch.meses_vigencia), 1)), _fmt(ch.realizado_total), _fmt(ch.previsto_total)])

    return PlantaTabela(
        table_object_id="tbl_ch_alocacao",
        slide_object_id=slide_id,
        cabecalhos=["Papel", "Mês", "Consumo", "Contrato"],
        linhas=linhas,
        larguras_polegadas=[1.45, 0.75, 0.75, 0.75],
        cor_status=COR_CABECALHO,
        layout=LayoutTabela(
            x_polegadas=x,
            y_polegadas=y,
            largura_polegadas=largura,
            altura_slide_polegadas=altura_slide,
        ),
    )


def _planta_resumo(
    ch: ControleHoras,
    slide_id: str,
    x: float,
    y: float,
    largura: float,
    altura_slide: float,
    titulo: str,
    referencia: date,
    ate_referencia: bool,
) -> PlantaTabela:
    linhas: list[list[str]] = []
    totais_prev = totais_exec = 0.0
    for funcao in (_FUNCAO_COORDENADOR, _FUNCAO_ARQUITETO, _FUNCAO_ANALISTA):
        if funcao not in ch.mensal_por_funcao and funcao not in ch.realizado_por_funcao:
            continue
        serie = ch.mensal_por_funcao.get(funcao, [])
        prev, exec_, saldo = _totais_periodo(serie, referencia, ate_referencia)
        if not serie:
            prev = ch.previsto_por_funcao.get(funcao, 0.0)
            exec_ = ch.realizado_por_funcao.get(funcao, 0.0)
            saldo = round(prev - exec_, 2)
        rotulo = {
            _FUNCAO_COORDENADOR: "Coordenação",
            _FUNCAO_ARQUITETO: "Arquiteto",
            _FUNCAO_ANALISTA: "Analista",
        }[funcao]
        linhas.append([rotulo, _fmt(prev, vazio_se_zero=True), _fmt(exec_), _fmt_saldo(prev, exec_)])
        totais_prev += prev
        totais_exec += exec_

    linhas.append(
        [
            "Total",
            _fmt(totais_prev, vazio_se_zero=True),
            _fmt(totais_exec),
            _fmt(round(totais_prev - totais_exec, 2)) if totais_prev else _fmt(-totais_exec),
        ]
    )

    return PlantaTabela(
        table_object_id=f"tbl_ch_{titulo.replace(' ', '_').lower()}",
        slide_object_id=slide_id,
        cabecalhos=[titulo, "Contrato", "Consumo", "Saldo"],
        linhas=linhas,
        larguras_polegadas=[1.45, 0.75, 0.75, 0.75],
        cor_status=COR_CABECALHO,
        layout=LayoutTabela(
            x_polegadas=x,
            y_polegadas=y,
            largura_polegadas=largura,
            altura_slide_polegadas=altura_slide,
        ),
    )


def _planta_mensal_funcao(
    rotulo: str,
    linhas_mes: list[LinhaMensalHoras],
    slide_id: str,
    x: float,
    y: float,
    largura: float,
    altura_slide: float,
    referencia: date,
    table_id: str,
    incluir_ano_mes: bool,
) -> PlantaTabela:
    linhas = [
        [_rotulo_mes(m.mes, incluir_ano_mes), _fmt(m.previsto, vazio_se_zero=True), _fmt(m.executado), _fmt_saldo(m.previsto, m.executado)]
        for m in linhas_mes
    ]
    prev_atual, exec_atual, saldo_atual = _totais_periodo(linhas_mes, referencia, True)
    prev_proj, exec_proj, saldo_proj = _totais_periodo(linhas_mes, referencia, False)
    linhas.append(["Atual", _fmt(prev_atual, vazio_se_zero=True), _fmt(exec_atual), _fmt_saldo(prev_atual, exec_atual)])
    linhas.append(["Projeto", _fmt(prev_proj, vazio_se_zero=True), _fmt(exec_proj), _fmt_saldo(prev_proj, exec_proj)])

    return PlantaTabela(
        table_object_id=table_id,
        slide_object_id=slide_id,
        cabecalhos=[rotulo, "Previsto", "Executado", "Saldo"],
        linhas=linhas,
        larguras_polegadas=[0.95, 0.7, 0.75, 0.65],
        cor_status=COR_CABECALHO,
        layout=LayoutTabela(
            x_polegadas=x,
            y_polegadas=y,
            largura_polegadas=largura,
            altura_slide_polegadas=altura_slide,
        ),
    )


def _plantas_analistas(
    blocos: list[BlocoAnalistaHoras],
    slide_id: str,
    largura_slide: float,
    altura_slide: float,
    remover: list[str],
    y_topo: float,
    referencia: date,
    indice_base: int,
    incluir_ano_mes: bool,
) -> list[PlantaTabela]:
    n = len(blocos)
    if n == 0:
        return []
    largura_tab = (largura_slide - 2 * _MARGEM - (n - 1) * _GAP) / n
    plantas: list[PlantaTabela] = []

    for indice, bloco in enumerate(blocos):
        linhas = [
            [
                _rotulo_mes(m.mes, incluir_ano_mes),
                _fmt(m.previsto, vazio_se_zero=True),
                _fmt(m.executado),
                _fmt_saldo(m.previsto, m.executado),
            ]
            for m in bloco.meses
        ]
        prev_atual, exec_atual, saldo_atual = _totais_periodo(bloco.meses, referencia, True)
        prev_proj, exec_proj, saldo_proj = _totais_periodo(bloco.meses, referencia, False)
        linhas.append(["Atual", _fmt(prev_atual, vazio_se_zero=True), _fmt(exec_atual), _fmt_saldo(prev_atual, exec_atual)])
        linhas.append(["Projeto", _fmt(prev_proj, vazio_se_zero=True), _fmt(exec_proj), _fmt_saldo(prev_proj, exec_proj)])

        nome_curto = bloco.analista.split()[0] if bloco.analista else "Analista"
        titulo = f"Analista {indice_base + indice + 1} ({nome_curto})"
        plantas.append(
            PlantaTabela(
                table_object_id=f"tbl_ch_an_{indice_base + indice}",
                slide_object_id=slide_id,
                cabecalhos=[titulo, "Previsto", "Executado", "Saldo"],
                linhas=linhas,
                larguras_polegadas=[0.85, 0.55, 0.6, 0.5],
                cor_status=COR_CABECALHO,
                layout=LayoutTabela(
                    x_polegadas=_MARGEM + indice * (largura_tab + _GAP),
                    y_polegadas=y_topo,
                    largura_polegadas=largura_tab,
                    altura_slide_polegadas=altura_slide,
                    margem_inferior_polegadas=0.25,
                ),
            )
        )
    return plantas


def _executar_plantas(slides, presentation_id: str, plantas: list[PlantaTabela]) -> None:
    criacao: list[dict] = []
    dimensoes: list[dict] = []
    for planta in plantas:
        reqs_criacao, reqs_dimensoes = requests_estrutura(planta)
        criacao.extend(reqs_criacao)
        dimensoes.extend(reqs_dimensoes)
    _executar(slides, presentation_id, criacao)
    _executar(slides, presentation_id, dimensoes)

    conteudo: list[dict] = []
    for planta in plantas:
        conteudo.extend(requests_conteudo(planta))
    _executar(slides, presentation_id, conteudo)


def _executar(slides, presentation_id: str, requests: list[dict]) -> None:
    if not requests:
        return
    (
        slides.presentations()
        .batchUpdate(presentationId=presentation_id, body={"requests": requests})
        .execute()
    )
