"""Pipeline de geracao de Status Report acionado pela coordenadora via GUI.

Fluxo:
1. Busca email da coordenadora na aba Coord_Status_Report.
2. Le o Google Calendar da coordenadora no dia informado.
3. Cruza eventos com a aba Clientes (ID completo vem do titulo do evento).
4. Processa cada cliente encontrado.
"""
from __future__ import annotations

from datetime import date
from typing import Callable

from status_report.aplicacao.fila_clientes_calendario import (
    CoordinadoraNaoEncontrada,
    buscar_coordenadora_na_planilha,
    montar_clientes_dos_eventos,
)
from status_report.aplicacao.pipeline_diario import _processar_cliente
from status_report.configuracao import Configuracoes
from status_report.dominio.modelos import ResultadoExecucao
from status_report.infraestrutura.autenticacao_google import (
    ServicosGoogle,
    construir_servico_calendario,
)
from status_report.infraestrutura.repositorio_calendario import (
    buscar_eventos_status_report,
)

LogFn = Callable[[str, str], None]


def _log(fn: LogFn, msg: str, tag: str = "info") -> None:
    fn(msg, tag)


def executar_pipeline_coordenadora(
    config: Configuracoes,
    servicos: ServicosGoogle,
    nome_coordenadora: str,
    data_referencia: date,
    log_fn: LogFn = lambda msg, tag: print(msg),
) -> list[ResultadoExecucao]:

    # 1. Busca coordenadora na planilha
    _log(log_fn, f"Buscando '{nome_coordenadora}' na planilha...")
    try:
        email_coordenadora, nome_coord = buscar_coordenadora_na_planilha(
            sheets=servicos.sheets,
            configuracoes=config,
            nome_coordenadora=nome_coordenadora,
        )
    except CoordinadoraNaoEncontrada as e:
        if e.similares:
            _log(log_fn, f"Coordenadora '{e.nome}' nao encontrada.", "erro")
            _log(log_fn, f"Voce quis dizer: {', '.join(e.similares)}?", "aviso")
        else:
            _log(log_fn, f"Coordenadora '{e.nome}' nao encontrada na planilha.", "erro")
            if e.nomes_disponiveis:
                _log(log_fn, f"Nomes cadastrados: {', '.join(e.nomes_disponiveis)}", "aviso")
        return []

    _log(log_fn, f"Coordenadora encontrada: {nome_coord} <{email_coordenadora}>", "ok")

    # 2. Le o calendario
    _log(log_fn, f"\nBuscando eventos em {data_referencia.strftime('%d/%m/%Y')} no calendario...")
    try:
        calendario = construir_servico_calendario(config, email_coordenadora)
        titulos_eventos = buscar_eventos_status_report(
            calendar=calendario,
            email_coordenadora=email_coordenadora,
            data=data_referencia,
            fuso_horario=config.fuso_horario,
        )
    except Exception as e:
        _log(log_fn, f"Erro ao acessar calendario de {email_coordenadora}: {e}", "erro")
        _log(log_fn, "Verifique se o escopo 'calendar.readonly' foi adicionado na delegacao de dominio.", "aviso")
        return []

    if not titulos_eventos:
        _log(log_fn, f"Nenhum evento 'Status Report' encontrado no dia {data_referencia.strftime('%d/%m/%Y')}.", "aviso")
        return []

    _log(log_fn, f"{len(titulos_eventos)} evento(s) encontrado(s):")
    for titulo in titulos_eventos:
        _log(log_fn, f"  • {titulo}")

    # 3. Cruza eventos com cadastro de clientes
    clientes = montar_clientes_dos_eventos(
        sheets=servicos.sheets,
        configuracoes=config,
        titulos_eventos=titulos_eventos,
        nome_coordenadora=nome_coord,
        email_coordenadora=email_coordenadora,
    )

    if not clientes:
        _log(log_fn, "\nNenhum cliente cadastrado correspondeu aos eventos do calendario.", "aviso")
        _log(log_fn, "Verifique a aba Clientes e se o codigo numerico do evento (ex: 131) esta cadastrado.", "aviso")
        return []

    _log(log_fn, f"\n{len(clientes)} cliente(s) para processar:")
    for c in clientes:
        _log(log_fn, f"  • {c.nome_curto} — {c.cliente_id_completo}")

    # 4. Processa cada cliente
    resultados: list[ResultadoExecucao] = []
    for cliente in clientes:
        _log(log_fn, f"\nProcessando: {cliente.nome_curto}...")
        try:
            resultado = _processar_cliente(
                configuracoes=config,
                servicos=servicos,
                cliente=cliente,
                data_referencia=data_referencia,
                log_fn=log_fn,
            )
            _log(log_fn, f"Concluido: {resultado.mensagem}", "ok")
            if resultado.url_pdf:
                _log(log_fn, f"Link: {resultado.url_pdf}", "ok")
            for caminho in resultado.caminhos_locais:
                _log(log_fn, f"Download: {caminho}", "ok")
            resultados.append(resultado)
        except Exception as e:
            _log(log_fn, f"Erro ao processar {cliente.nome_curto}: {e}", "erro")
            resultados.append(
                ResultadoExecucao(
                    cliente=cliente.nome_curto,
                    sucesso=False,
                    url_pdf="",
                    mensagem=str(e),
                )
            )

    return resultados
