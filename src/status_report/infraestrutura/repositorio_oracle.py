"""Acesso ao banco Oracle (ERP GHR) via python-oracledb em modo thin.

O modo thin nao exige o Oracle Instant Client — a conexao e feita direto em
Python. As credenciais e o endereco vem das configuracoes (arquivo .env).
"""
from __future__ import annotations

import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path

import oracledb

from status_report.configuracao import Configuracoes
from status_report.dominio.modelos import (
    LinhaHorasPlanejado,
    LinhaHorasPrevistoEtapa,
    LinhaHorasRealizado,
    ProjetoOracle,
)


class OracleNaoConfigurado(Exception):
    """Lancada quando faltam credenciais do Oracle no .env."""


class OracleClientIndisponivel(Exception):
    """Lancada quando o Oracle Instant Client (modo thick) nao pode ser iniciado."""


_thick_iniciado = False


def _caminho_ascii_seguro(caminho: str) -> str:
    """No Windows, o Oracle Client nao carrega de caminhos com caracteres nao-ASCII
    (ex.: "Área de Trabalho"). Converte para o caminho curto 8.3, que e ASCII.
    """
    if os.name != "nt" or caminho.isascii():
        return caminho
    import ctypes
    from ctypes import wintypes

    obter_curto = ctypes.windll.kernel32.GetShortPathNameW
    obter_curto.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    obter_curto.restype = wintypes.DWORD
    tamanho = obter_curto(caminho, None, 0)
    if tamanho == 0:
        return caminho
    buffer = ctypes.create_unicode_buffer(tamanho)
    if obter_curto(caminho, buffer, tamanho) == 0:
        return caminho
    return buffer.value or caminho


def _bases_de_busca() -> list[Path]:
    """Pastas onde procurar o Instant Client empacotado."""
    bases: list[Path] = []
    if getattr(sys, "frozen", False):  # executavel PyInstaller
        bases.append(Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)))
        bases.append(Path(sys.executable).parent)
    # raiz do projeto (execucao via codigo-fonte)
    bases.append(Path(__file__).resolve().parents[3])
    return bases


def _resolver_lib_dir(config: Configuracoes) -> str | None:
    """Descobre a pasta do Instant Client.

    Prioridade: ORACLE_CLIENT_LIB_DIR do .env; senao uma pasta ``instantclient*``
    na raiz do projeto / ao lado do executavel. None deixa o driver procurar no PATH.
    """
    if config.oracle_client_lib_dir:
        return _caminho_ascii_seguro(config.oracle_client_lib_dir)
    for base in _bases_de_busca():
        for nome in ("instantclient_21_17", "instantclient"):
            candidato = base / nome
            if candidato.is_dir():
                return _caminho_ascii_seguro(str(candidato))
        for candidato in sorted(base.glob("instantclient*")):
            if candidato.is_dir():
                return _caminho_ascii_seguro(str(candidato))
    return None


def _garantir_thick_mode(config: Configuracoes) -> None:
    """Inicia o modo thick (Instant Client) uma unica vez.

    O ERP usa um verificador de senha antigo (10g), que o modo thin nao suporta.
    Por isso o Instant Client e obrigatorio.
    """
    global _thick_iniciado
    if _thick_iniciado:
        return
    lib_dir = _resolver_lib_dir(config)
    try:
        oracledb.init_oracle_client(lib_dir=lib_dir)
    except Exception as e:  # noqa: BLE001
        raise OracleClientIndisponivel(
            "Nao foi possivel iniciar o Oracle Instant Client (modo thick). "
            "Verifique ORACLE_CLIENT_LIB_DIR no .env apontando para a pasta do "
            f"Instant Client 64-bit. Detalhe: {e}"
        ) from e
    _thick_iniciado = True


# SQL: projetos ativos (ie_status = 'E') vinculados a um cliente.
_SQL_PROJETOS_DO_CLIENTE = """
    SELECT p.nr_sequencia AS cd,
           p.ds_titulo    AS ds
      FROM proj_projeto p
     WHERE p.nr_seq_cliente = :nr_seq_cliente
       AND p.ie_status = 'E'
     ORDER BY p.ds_titulo
"""

# SQL: todos os clientes (o codigo padronizado fica no inicio de nm_fantasia).
_SQL_CLIENTES = """
    SELECT c.nr_sequencia AS cd,
           j.nm_fantasia  AS ds
      FROM com_cliente     c,
           pessoa_juridica j
     WHERE c.cd_cnpj = j.cd_cgc
     ORDER BY j.nm_fantasia
"""

_RE_CODIGO_INICIAL = re.compile(r"^\s*(\d+)")


# Controle de Horas - Consulta A (Planejado): cabecalho + previsto por cronograma.
_SQL_HORAS_PLANEJADO = """
    SELECT
        c.nm_fantasia                                            AS nome_cliente,
        p.nr_sequencia                                           AS nr_seq_proj,
        p.ds_titulo                                              AS nome_projeto,
        d.nr_sequencia                                           AS seq_crono,
        d.ds_objetivo                                            AS objetivo_cronograma,
        d.dt_inicio                                              AS dt_inicio,
        d.dt_fim                                                 AS dt_fim,
        d.qt_total_horas                                         AS horas_previstas_total,
        d.qt_horas_realizado                                     AS horas_realizado_total,
        TRUNC(MONTHS_BETWEEN(d.dt_fim, d.dt_inicio)) + 1         AS qt_meses,
        ROUND(d.qt_total_horas
            / NULLIF(TRUNC(MONTHS_BETWEEN(d.dt_fim, d.dt_inicio)) + 1, 0), 2)
                                                                AS horas_previstas_mes
    FROM
             proj_cronograma d
        JOIN proj_projeto    p ON d.nr_seq_proj    = p.nr_sequencia
        JOIN com_cliente     b ON d.nr_seq_cliente = b.nr_sequencia
        JOIN pessoa_juridica c ON b.cd_cnpj        = c.cd_cgc
    WHERE
            p.ie_status = 'E'
        AND ( d.nr_seq_cliente = :nr_seq_cliente OR :nr_seq_cliente = 0 )
        AND ( p.nr_sequencia   = :nr_seq_proj    OR :nr_seq_proj    = 0 )
    ORDER BY
        d.nr_sequencia
"""

# Controle de Horas - Consulta B (Realizado): executado por analista/funcao/mes.
_SQL_HORAS_REALIZADO = """
    SELECT
        p.nr_sequencia                                AS nr_seq_proj,
        d.nr_sequencia                                AS seq_crono,
        to_char(ra.dt_inicio_ativ, 'MM/YYYY')         AS mes,
        r.cd_executor                                 AS cd_executor,
        obter_nome_pf(r.cd_executor)                  AS analista,
        CASE
            WHEN upper(e.ds_atividade) LIKE '%MONITORAMENTO E CONTROLE%'
                 AND e.ie_fase = 'N' THEN 'COORDENADOR'
            WHEN e.nr_seq_etapa = 116 THEN 'COORDENADOR'
            WHEN upper(e.ds_atividade) LIKE '%ARQUI%'
                 AND e.ie_fase = 'N' THEN 'ARQUITETO'
            WHEN e.nr_seq_etapa = 115 THEN 'ARQUITETO'
            ELSE 'ANALISTA'
        END                                           AS funcao,
        ROUND(SUM(ra.qt_min_ativ) / 60, 2)            AS horas_trabalhadas
    FROM
             proj_cronograma d
        JOIN proj_projeto    p  ON d.nr_seq_proj        = p.nr_sequencia
        JOIN proj_cron_etapa e  ON d.nr_sequencia       = e.nr_seq_cronograma
        JOIN proj_rat_ativ   ra ON ra.nr_seq_etapa_cron = e.nr_sequencia
        JOIN proj_rat        r  ON ra.nr_seq_rat        = r.nr_sequencia
                               AND r.nr_seq_proj        = p.nr_sequencia
    WHERE
            p.ie_status = 'E'
        AND ( d.nr_seq_cliente = :nr_seq_cliente OR :nr_seq_cliente = 0 )
        AND ( p.nr_sequencia   = :nr_seq_proj    OR :nr_seq_proj    = 0 )
    GROUP BY
        p.nr_sequencia, d.nr_sequencia,
        to_char(ra.dt_inicio_ativ, 'MM/YYYY'),
        r.cd_executor, e.ie_fase, e.nr_seq_etapa, e.ds_atividade
    ORDER BY
        funcao, analista, mes
"""


# Controle de Horas - Consulta C (Previsto por etapa/cargo).
# Usa apenas etapas folha (ie_fase = 'N') para evitar duplicar totais agregados.
_SQL_CASE_FUNCAO_ETAPA = """
        CASE
            WHEN upper(e.ds_atividade) LIKE '%MONITORAMENTO E CONTROLE%'
                 AND e.ie_fase = 'N' THEN 'COORDENADOR'
            WHEN e.nr_seq_etapa = 116 THEN 'COORDENADOR'
            WHEN upper(e.ds_atividade) LIKE '%ARQUI%'
                 AND e.ie_fase = 'N' THEN 'ARQUITETO'
            WHEN e.nr_seq_etapa = 115 THEN 'ARQUITETO'
            ELSE 'ANALISTA'
        END
"""

_SQL_HORAS_PREVISTO_ETAPAS = f"""
    SELECT
        p.nr_sequencia                                AS nr_seq_proj,
        d.nr_sequencia                                AS seq_crono,
        d.ds_objetivo                                 AS objetivo_cronograma,
        d.dt_inicio                                   AS crono_inicio,
        d.dt_fim                                      AS crono_fim,
        e.nr_sequencia                                AS seq_etapa,
        e.ds_atividade                                AS ds_atividade,
        e.qt_hora_prev                                AS horas_previstas,
        e.dt_inicio_prev                              AS dt_inicio_prev,
        e.dt_fim_prev                                 AS dt_fim_prev,
        {_SQL_CASE_FUNCAO_ETAPA.strip()}              AS funcao
    FROM
             proj_cronograma d
        JOIN proj_projeto    p ON d.nr_seq_proj = p.nr_sequencia
        JOIN proj_cron_etapa e ON d.nr_sequencia = e.nr_seq_cronograma
    WHERE
            p.ie_status = 'E'
        AND e.ie_fase = 'N'
        AND NVL(e.qt_hora_prev, 0) > 0
        AND ( d.nr_seq_cliente = :nr_seq_cliente OR :nr_seq_cliente = 0 )
        AND ( p.nr_sequencia   = :nr_seq_proj    OR :nr_seq_proj    = 0 )
    ORDER BY
        d.nr_sequencia, e.nr_sequencia
"""


def _num(valor) -> float:
    return float(valor) if valor is not None else 0.0


@contextmanager
def conectar(config: Configuracoes):
    """Abre uma conexao Oracle (thin mode) a partir das configuracoes."""
    if not config.oracle_configurado():
        raise OracleNaoConfigurado(
            "Credenciais do Oracle ausentes. Preencha ORACLE_USER, ORACLE_PASSWORD, "
            "ORACLE_HOST e ORACLE_SERVICE_NAME no .env."
        )
    _garantir_thick_mode(config)
    conexao = oracledb.connect(
        user=config.oracle_usuario,
        password=config.oracle_senha,
        dsn=config.oracle_dsn(),
        tcp_connect_timeout=10,
    )
    try:
        _definir_schema(conexao, config.oracle_schema)
        yield conexao
    finally:
        conexao.close()


def _definir_schema(conexao, schema: str) -> None:
    """Define o CURRENT_SCHEMA da sessao (tabelas do ERP ficam no schema GHR)."""
    schema = (schema or "").strip()
    if not schema or not schema.replace("_", "").isalnum():
        return
    with conexao.cursor() as cursor:
        cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {schema}")


def listar_projetos_ativos_do_cliente(
    config: Configuracoes, nr_seq_cliente: int | str
) -> list[ProjetoOracle]:
    """Retorna os projetos ativos do cliente informado (ordenados por titulo)."""
    with conectar(config) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                _SQL_PROJETOS_DO_CLIENTE,
                nr_seq_cliente=int(nr_seq_cliente),
            )
            linhas = cursor.fetchall()
    return [
        ProjetoOracle(nr_seq_proj=int(cd), titulo=str(ds or "").strip())
        for cd, ds in linhas
    ]


def _codigo_inicial(nm_fantasia: str) -> int | None:
    """Extrai o codigo numerico do inicio do nome fantasia (ex.: '099 - Ghr' -> 99)."""
    achado = _RE_CODIGO_INICIAL.match(nm_fantasia or "")
    return int(achado.group(1)) if achado else None


def carregar_mapa_codigo_para_nr_seq(config: Configuracoes) -> dict[int, int]:
    """Mapa {codigo_do_cliente -> nr_sequencia} lido do ERP.

    O codigo e o numero padronizado no inicio de ``nm_fantasia`` (com_cliente).
    """
    with conectar(config) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(_SQL_CLIENTES)
            linhas = cursor.fetchall()
    mapa: dict[int, int] = {}
    for cd, ds in linhas:
        codigo = _codigo_inicial(str(ds or ""))
        if codigo is not None and codigo not in mapa:
            mapa[codigo] = int(cd)
    return mapa


def consultar_horas_planejado(
    config: Configuracoes,
    nr_seq_cliente: int | str = 0,
    nr_seq_proj: int | str = 0,
) -> list[LinhaHorasPlanejado]:
    """Consulta A do Controle de Horas: previsto/realizado por cronograma."""
    with conectar(config) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                _SQL_HORAS_PLANEJADO,
                nr_seq_cliente=int(nr_seq_cliente or 0),
                nr_seq_proj=int(nr_seq_proj or 0),
            )
            linhas = cursor.fetchall()
    return [
        LinhaHorasPlanejado(
            nome_cliente=str(l[0] or "").strip(),
            nr_seq_proj=int(l[1]),
            nome_projeto=str(l[2] or "").strip(),
            seq_crono=int(l[3]),
            objetivo_cronograma=str(l[4] or "").strip(),
            dt_inicio=l[5],
            dt_fim=l[6],
            horas_previstas_total=_num(l[7]),
            horas_realizado_total=_num(l[8]),
            qt_meses=int(l[9] or 0),
            horas_previstas_mes=_num(l[10]),
        )
        for l in linhas
    ]


def consultar_horas_realizado(
    config: Configuracoes,
    nr_seq_cliente: int | str = 0,
    nr_seq_proj: int | str = 0,
) -> list[LinhaHorasRealizado]:
    """Consulta B do Controle de Horas: executado por analista/funcao/mes."""
    with conectar(config) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                _SQL_HORAS_REALIZADO,
                nr_seq_cliente=int(nr_seq_cliente or 0),
                nr_seq_proj=int(nr_seq_proj or 0),
            )
            linhas = cursor.fetchall()
    return [
        LinhaHorasRealizado(
            nr_seq_proj=int(l[0]),
            seq_crono=int(l[1]),
            mes=str(l[2] or "").strip(),
            cd_executor=int(l[3] or 0),
            analista=str(l[4] or "").strip(),
            funcao=str(l[5] or "").strip(),
            horas_trabalhadas=_num(l[6]),
        )
        for l in linhas
    ]


def consultar_horas_previsto_etapas(
    config: Configuracoes,
    nr_seq_cliente: int | str = 0,
    nr_seq_proj: int | str = 0,
) -> list[LinhaHorasPrevistoEtapa]:
    """Consulta C do Controle de Horas: previsto por etapa e cargo."""
    with conectar(config) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                _SQL_HORAS_PREVISTO_ETAPAS,
                nr_seq_cliente=int(nr_seq_cliente or 0),
                nr_seq_proj=int(nr_seq_proj or 0),
            )
            linhas = cursor.fetchall()
    return [
        LinhaHorasPrevistoEtapa(
            nr_seq_proj=int(l[0]),
            seq_crono=int(l[1]),
            objetivo_cronograma=str(l[2] or "").strip(),
            crono_inicio=l[3],
            crono_fim=l[4],
            seq_etapa=int(l[5]),
            ds_atividade=str(l[6] or "").strip(),
            horas_previstas=_num(l[7]),
            dt_inicio_prev=l[8],
            dt_fim_prev=l[9],
            funcao=str(l[10] or "").strip(),
        )
        for l in linhas
    ]


def testar_conexao(config: Configuracoes) -> str:
    """Executa um SELECT trivial para validar credenciais/rede. Retorna a versao."""
    with conectar(config) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
            (banner,) = cursor.fetchone()
    return str(banner)
