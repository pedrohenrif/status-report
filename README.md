# Automacao de Status Report

Projeto Python para gerar Status Reports automaticamente com dados do Google Sheets, preenchendo template no Google Slides e publicando o PDF final em uma pasta do Google Drive.

## Fluxo

1. Roda apenas em dias uteis (segunda a sexta).
2. Le na aba `Fila_StatusReport` quais clientes precisam de relatorio no dia.
3. Para cada cliente:
   - copia o template do Slides
   - aplica todos os renderizadores ativos (substituicao de placeholders)
   - exporta para PDF
   - publica na pasta final do Drive

## Arquitetura

```
src/status_report/
  configuracao.py            # Settings carregados do .env
  main.py                    # Entrypoint CLI
  dominio/
    modelos.py               # ClienteFila, DadosRelatorio, ResultadoExecucao
  infraestrutura/
    autenticacao_google.py   # Service account + clientes Sheets/Slides/Drive
    repositorio_planilha.py  # Leitura no Sheets
    repositorio_apresentacao.py # batchUpdate no Slides
    repositorio_drive.py     # copia, exporta PDF, publica na pasta
  aplicacao/
    fila_clientes.py         # Filtra clientes do dia
    renderizacao_relatorio.py# Agrega substituicoes dos renderizadores
    pipeline_diario.py       # Orquestra tudo
  renderizadores/
    protocolo.py             # Contrato RenderizadorSlide
    registro.py              # Lista de renderizadores ativos
    slide_capa.py            # Slide 1 (capa)
```

Para incluir um novo slide na automacao, basta criar um arquivo
`renderizadores/<nome>.py` que implemente `coletar_substituicoes` e adicionar
sua instancia em `renderizadores/registro.py`.

## Como executar

1. Instalar dependencias:

```bash
poetry install
```

2. Criar `.env` a partir de `.env.example` e preencher os IDs.
3. Executar:

```bash
poetry run python -m status_report.main
```

Opcoes:

```bash
poetry run python -m status_report.main --date 2026-05-06
poetry run python -m status_report.main --force-run
poetry run python -m status_report.main --dry-run
```

## Variaveis do `.env`

- `GOOGLE_SERVICE_ACCOUNT_FILE`: caminho do JSON da service account.
- `GOOGLE_SERVICE_ACCOUNT_EMAIL`: email da service account.
- `GOOGLE_SPREADSHEET_ID`: planilha principal com a fila e os dados.
- `GOOGLE_TEMPLATE_PRESENTATION_ID`: template no Google Slides.
- `GOOGLE_OUTPUT_FOLDER_ID`: pasta de saida no Drive.
- `GOOGLE_CLIENT_QUEUE_RANGE`: intervalo da fila (padrao `Fila_StatusReport!A2:F`).
- `GOOGLE_DATA_RANGE`: intervalo base para extracao dos dados.

## Aba `Fila_StatusReport`

Layout esperado (cabecalhos na linha 1, dados a partir da linha 2):

| A: nome_curto  | B: ativo | C: dias_semana        | D: coordenadora | E: cliente_id_completo            | F: nome_pdf_customizado |
|----------------|----------|-----------------------|-----------------|-----------------------------------|-------------------------|
| 131 - Honorp   | TRUE     | SEG,TER,QUA,QUI,SEX   | Pedro Furtado   | 131-ID: 0078-25 HONORP - SUPCON   | (vazio)                 |

Regras:

- `ativo = FALSE` ignora a linha.
- `dias_semana` em branco => roda todo dia util.
- `nome_pdf_customizado` em branco => usa `Status Report - <nome_curto> - <data>.pdf`.

## Agendamento (seg-sex)

- Use o Windows Task Scheduler para rodar 1x ao dia, seg-sex.
- O codigo tambem valida o dia da semana internamente.
