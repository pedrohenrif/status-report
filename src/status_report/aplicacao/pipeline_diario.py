"""Pipeline diario do Status Report.

Responsabilidades:

1. Validar dia util (segunda a sexta) salvo execucao forcada.
2. Buscar fila de clientes do dia.
3. Para cada cliente:
   - copiar template no Drive,
   - aplicar substituicoes de todos os renderizadores ativos,
   - exportar para PDF e publicar na pasta final,
   - opcionalmente remover a copia temporaria do Slides.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Callable
from zoneinfo import ZoneInfo

from status_report.aplicacao.fila_clientes import buscar_clientes_do_dia
from status_report.aplicacao.projeto_funcional import agrupar_por_status
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
from status_report.infraestrutura.repositorio_projeto_funcional import (
    extrair_id_planilha,
    ler_itens_projeto_funcional,
)
from status_report.renderizadores.registro import RENDERIZADORES_ATIVOS

LogFn = Callable[[str, str], None]


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
        grupos = _carregar_grupos_projeto_funcional(
            configuracoes=configuracoes,
            servicos=servicos,
            cliente=cliente,
            log_fn=log_fn,
        )
        if grupos is not None:
            substituicoes.update(substituicoes_quantidade_projeto_funcional(grupos))
        aplicar_substituicoes(
            slides=servicos.slides,
            id_apresentacao=id_copia,
            substituicoes=substituicoes,
        )
        if grupos is not None:
            renderizar_tabelas_projeto_funcional(
                slides=servicos.slides,
                presentation_id=id_copia,
                grupos=grupos,
            )
        link_arquivo = obter_link_arquivo(drive=servicos.drive, id_arquivo=id_copia)
    except Exception:
        remover_arquivo(drive=servicos.drive, id_arquivo=id_copia)
        raise

    return ResultadoExecucao(
        cliente=cliente.nome_curto,
        sucesso=True,
        url_pdf=link_arquivo,
        mensagem="Apresentacao publicada com sucesso.",
    )


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
