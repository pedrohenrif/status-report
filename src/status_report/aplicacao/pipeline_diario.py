"""Pipeline diario do Status Report.

Responsabilidades:

1. Validar dia util (segunda a sexta) salvo execucao forcada.
2. Buscar fila de clientes do dia.
3. Para cada cliente:
   - copiar template no Drive,
   - aplicar substituicoes de todos os renderizadores ativos,
   - publicar copia no Drive e salvar .pptx localmente (opcional),
   - opcionalmente remover a copia temporaria do Slides.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Callable
from zoneinfo import ZoneInfo

from status_report.aplicacao.agregacao_controle_horas import montar_controle_horas
from status_report.aplicacao.fila_clientes import buscar_clientes_do_dia
from status_report.aplicacao.projeto_funcional import agrupar_por_status
from status_report.aplicacao.render_controle_horas import renderizar_controle_horas
from status_report.aplicacao.render_projeto_funcional import (
    renderizar_tabelas_projeto_funcional,
    substituicoes_quantidade_projeto_funcional,
)
from status_report.aplicacao.renderizacao_relatorio import (
    coletar_substituicoes_de_todos,
)
from status_report.configuracao import Configuracoes
from status_report.dominio.modelos import (
    ClienteFila,
    DadosRelatorio,
    ProjetoFuncionalAgrupado,
    ResultadoExecucao,
)
from status_report.infraestrutura.autenticacao_google import (
    ServicosGoogle,
    construir_servicos_google,
)
from status_report.infraestrutura.repositorio_apresentacao import (
    aplicar_substituicoes,
)
from status_report.infraestrutura.repositorio_drive import (
    baixar_apresentacoes_locais,
    copiar_apresentacao,
    criar_ou_obter_subpasta,
    obter_link_arquivo,
    remover_arquivo,
)
from status_report.infraestrutura.repositorio_indice_projetos import (
    ProjetoNaoEncontradoNoIndice,
    buscar_link_por_codigo_projeto,
    extrair_codigo_projeto,
)
from status_report.infraestrutura.repositorio_oracle import (
    consultar_horas_planejado,
    consultar_horas_previsto_etapas,
    consultar_horas_realizado,
)
from status_report.infraestrutura.repositorio_projeto_funcional import (
    extrair_id_planilha,
    ler_itens_projeto_funcional,
)
from status_report.infraestrutura.repositorio_slides_modelo import (
    duplicar_slide,
    indice_do_slide,
    mapear_slides_modelo,
    mover_slides,
    remover_slides,
)
from status_report.renderizadores.registro import RENDERIZADORES_ATIVOS

LogFn = Callable[[str, str], None]

_MARCADORES_MODELO = (
    "MODELO_CONTROLE_HORAS",
    "MODELO_CONTROLE_HORAS_ANALISTAS",
    "MODELO_PF_CONCLUIDOS",
    "MODELO_PF_PENDENTES",
    "MODELO_PF_EM_ANDAMENTO",
)


def _sem_log(mensagem: str, tag: str = "info") -> None:
    return None


def executar_pipeline_diario(
    configuracoes: Configuracoes,
    data_referencia: date,
    forcar_execucao: bool = False,
) -> list[ResultadoExecucao]:
    if (
        configuracoes.rodar_apenas_dias_uteis
        and not forcar_execucao
        and data_referencia.weekday() >= 5
    ):
        return [
            ResultadoExecucao(
                cliente="-",
                sucesso=True,
                url_pdf="",
                mensagem="Execucao ignorada: fim de semana.",
            )
        ]

    servicos = construir_servicos_google(configuracoes)
    clientes = buscar_clientes_do_dia(
        sheets=servicos.sheets,
        configuracoes=configuracoes,
        data_referencia=data_referencia,
    )
    if not clientes:
        return [
            ResultadoExecucao(
                cliente="-",
                sucesso=True,
                url_pdf="",
                mensagem="Nenhum cliente na fila para hoje.",
            )
        ]

    resultados: list[ResultadoExecucao] = []
    for cliente in clientes:
        try:
            resultado = _processar_cliente(
                configuracoes=configuracoes,
                servicos=servicos,
                cliente=cliente,
                data_referencia=data_referencia,
            )
        except Exception as erro:
            resultado = ResultadoExecucao(
                cliente=cliente.nome_curto,
                sucesso=False,
                url_pdf="",
                mensagem=f"Erro no processamento: {erro}",
            )
        resultados.append(resultado)
    return resultados


def construir_data_referencia(fuso_horario: str) -> date:
    fuso = ZoneInfo(fuso_horario)
    return datetime.now(tz=fuso).date()


def _processar_cliente(
    configuracoes: Configuracoes,
    servicos: ServicosGoogle,
    cliente: ClienteFila,
    data_referencia: date,
    log_fn: LogFn = _sem_log,
) -> ResultadoExecucao:
    if configuracoes.modo_simulacao:
        return ResultadoExecucao(
            cliente=cliente.nome_curto,
            sucesso=True,
            url_pdf="",
            mensagem="MODO_SIMULACAO: cliente identificado e pronto para processamento.",
        )

    dados = DadosRelatorio(cliente=cliente, data_referencia=data_referencia)
    substituicoes = coletar_substituicoes_de_todos(
        renderizadores=RENDERIZADORES_ATIVOS,
        dados=dados,
    )

    id_subpasta = criar_ou_obter_subpasta(
        drive=servicos.drive,
        id_pasta_pai=configuracoes.id_pasta_saida,
        nome=data_referencia.strftime("%Y-%m-%d"),
    )
    nome_arquivo = cliente.nome_arquivo_pdf(data_referencia)
    id_copia = copiar_apresentacao(
        drive=servicos.drive,
        id_modelo=configuracoes.id_apresentacao_modelo,
        nome_da_copia=nome_arquivo,
        id_pasta_destino=id_subpasta,
    )
    try:
        modelos = mapear_slides_modelo(servicos.slides, id_copia)

        grupos = _carregar_grupos_projeto_funcional(
            configuracoes=configuracoes,
            servicos=servicos,
            cliente=cliente,
            log_fn=log_fn,
        )
        if grupos is not None:
            substituicoes.update(substituicoes_quantidade_projeto_funcional(grupos))
        else:
            substituicoes.update(
                {
                    "{{QTD_CONCLUIDOS}}": "0",
                    "{{QTD_PENDENTES}}": "0",
                    "{{QTD_EM_ANDAMENTO}}": "0",
                }
            )
        # Limpa os marcadores de modelo ({{MODELO_*}}) da apresentacao gerada.
        for marcador in _MARCADORES_MODELO:
            substituicoes[f"{{{{{marcador}}}}}"] = ""

        aplicar_substituicoes(
            slides=servicos.slides,
            id_apresentacao=id_copia,
            substituicoes=substituicoes,
        )

        slides_para_remover: list[str] = []
        _renderizar_controle_horas(
            configuracoes=configuracoes,
            servicos=servicos,
            cliente=cliente,
            id_copia=id_copia,
            modelos=modelos,
            slides_para_remover=slides_para_remover,
            data_referencia=data_referencia,
            log_fn=log_fn,
        )

        if grupos is not None:
            slides_por_chave = {
                chave: modelos[marcador]
                for chave, marcador in (
                    ("concluidos", "MODELO_PF_CONCLUIDOS"),
                    ("pendentes", "MODELO_PF_PENDENTES"),
                    ("em_andamento", "MODELO_PF_EM_ANDAMENTO"),
                )
                if marcador in modelos
            }
            renderizar_tabelas_projeto_funcional(
                slides=servicos.slides,
                presentation_id=id_copia,
                grupos=grupos,
                slides_por_chave=slides_por_chave or None,
            )

        if slides_para_remover:
            remover_slides(servicos.slides, id_copia, slides_para_remover)

        link_arquivo = obter_link_arquivo(drive=servicos.drive, id_arquivo=id_copia)
        caminhos_locais = _salvar_download_local(
            configuracoes=configuracoes,
            servicos=servicos,
            id_copia=id_copia,
            data_referencia=data_referencia,
            nome_arquivo=nome_arquivo,
            log_fn=log_fn,
        )
    except Exception:
        remover_arquivo(drive=servicos.drive, id_arquivo=id_copia)
        raise

    return ResultadoExecucao(
        cliente=cliente.nome_curto,
        sucesso=True,
        url_pdf=link_arquivo,
        mensagem="Apresentacao publicada com sucesso.",
        caminhos_locais=caminhos_locais,
    )


def _salvar_download_local(
    configuracoes: Configuracoes,
    servicos: ServicosGoogle,
    id_copia: str,
    data_referencia: date,
    nome_arquivo: str,
    log_fn: LogFn,
) -> list[str]:
    if not configuracoes.salvar_download_local:
        return []
    salvos, avisos = baixar_apresentacoes_locais(
        drive=servicos.drive,
        id_apresentacao=id_copia,
        pasta_base=configuracoes.pasta_download_local_resolvida(),
        data_referencia=data_referencia,
        nome_arquivo=nome_arquivo,
    )
    for caminho in salvos:
        rotulo = "PDF" if caminho.suffix.lower() == ".pdf" else "PowerPoint"
        log_fn(f"{rotulo} salvo localmente: {caminho}", "ok")
    for aviso in avisos:
        log_fn(f"Aviso: {aviso}", "aviso")
    return [str(caminho) for caminho in salvos]


def _renderizar_controle_horas(
    configuracoes: Configuracoes,
    servicos: ServicosGoogle,
    cliente: ClienteFila,
    id_copia: str,
    modelos: dict[str, str],
    slides_para_remover: list[str],
    data_referencia: date,
    log_fn: LogFn,
) -> None:
    """Preenche os slides de Controle de Horas ou os marca para remocao."""
    id_principal = modelos.get("MODELO_CONTROLE_HORAS")
    id_analistas = modelos.get("MODELO_CONTROLE_HORAS_ANALISTAS")
    if id_principal is None:
        return

    ch = _carregar_controle_horas(configuracoes, cliente, log_fn)
    if ch is None:
        slides_para_remover.extend(
            sid for sid in (id_principal, id_analistas) if sid
        )
        return

    ids_analistas: list[str] = []
    if id_analistas:
        analistas = [b for b in ch.analistas if b.funcao == "ANALISTA"]
        lotes = max(1, (len(analistas) + 2) // 3)
        ids_analistas = [id_analistas]
        for _ in range(lotes - 1):
            copia = duplicar_slide(servicos.slides, id_copia, id_analistas)
            base = indice_do_slide(servicos.slides, id_copia, id_analistas)
            mover_slides(servicos.slides, id_copia, [copia], base + 1)
            ids_analistas.append(copia)

    slides_para_remover.extend(
        renderizar_controle_horas(
            slides=servicos.slides,
            presentation_id=id_copia,
            slide_principal_id=id_principal,
            slide_analistas_ids=ids_analistas or None,
            ch=ch,
            data_referencia=data_referencia,
        )
    )


def _carregar_controle_horas(
    configuracoes: Configuracoes,
    cliente: ClienteFila,
    log_fn: LogFn,
):
    """Consulta o ERP e agrega o Controle de Horas do projeto selecionado."""
    if not configuracoes.oracle_configurado():
        log_fn("Aviso: Oracle nao configurado; Controle de Horas nao gerado.", "aviso")
        return None
    nr_seq_proj = (cliente.nr_seq_proj or "").strip()
    if not nr_seq_proj:
        log_fn(
            "Aviso: projeto nao selecionado; Controle de Horas nao gerado.", "aviso"
        )
        return None
    nr_seq_cliente = (cliente.nr_seq_cliente or "").strip() or 0
    try:
        planejado = consultar_horas_planejado(configuracoes, nr_seq_cliente, nr_seq_proj)
        realizado = consultar_horas_realizado(configuracoes, nr_seq_cliente, nr_seq_proj)
        previsto_etapas = consultar_horas_previsto_etapas(
            configuracoes, nr_seq_cliente, nr_seq_proj
        )
    except Exception as erro:
        log_fn(f"Aviso: falha ao consultar Controle de Horas no ERP: {erro}", "aviso")
        return None

    ch = montar_controle_horas(planejado, realizado, previsto_etapas)
    if ch is None:
        log_fn("Aviso: sem dados de Controle de Horas para o projeto.", "aviso")
    else:
        log_fn(
            f"Controle de Horas: previsto {ch.previsto_total}h, "
            f"realizado {ch.realizado_total}h.",
            "info",
        )
    return ch


def _carregar_grupos_projeto_funcional(
    configuracoes: Configuracoes,
    servicos: ServicosGoogle,
    cliente: ClienteFila,
    log_fn: LogFn,
) -> ProjetoFuncionalAgrupado | None:
    """Le e agrupa itens do Projeto Funcional. Falhas retornam None."""
    codigo_projeto = extrair_codigo_projeto(cliente.cliente_id_completo)
    if not codigo_projeto:
        log_fn(
            f"Aviso: nao identifiquei o codigo do projeto em "
            f"'{cliente.cliente_id_completo}'. Tabelas nao geradas.",
            "aviso",
        )
        return None

    try:
        link = buscar_link_por_codigo_projeto(
            sheets=servicos.sheets,
            configuracoes=configuracoes,
            codigo_projeto=codigo_projeto,
        )
        _, itens = ler_itens_projeto_funcional(
            sheets=servicos.sheets,
            drive=servicos.drive,
            spreadsheet_id=extrair_id_planilha(link),
        )
        grupos = agrupar_por_status(itens)
        log_fn(
            f"Projeto {codigo_projeto}: {grupos.total_concluidos} concluidos, "
            f"{grupos.total_em_andamento} em andamento, "
            f"{grupos.total_pendentes} pendentes.",
            "info",
        )
        return grupos
    except ProjetoNaoEncontradoNoIndice:
        log_fn(
            f"Aviso: projeto {codigo_projeto} nao esta na aba Projetos_Funcionais. "
            "Tabelas nao geradas.",
            "aviso",
        )
        return None
    except Exception as erro:
        log_fn(f"Aviso: falha ao montar tabelas do Projeto Funcional: {erro}", "aviso")
        return None
