# Automação de Status Report — GHR Tech

Projeto Python para gerar **Status Reports** automaticamente a partir de dados operacionais (Google Sheets, Google Calendar e planilhas de Projeto Funcional), preenchendo um template no **Google Slides** e publicando a apresentação final em uma pasta do **Google Drive**.

Cada coordenadora pode rodar o processo de forma autônoma pela **interface gráfica (tkinter)**, informando seu nome e a data desejada. O sistema consulta a agenda dela, identifica os clientes do dia e gera os relatórios.

---

## Objetivos do projeto

1. **Eliminar trabalho manual** de copiar prints da planilha para o slide.
2. **Padronizar** a geração de Status Reports com template fixo e dados consistentes.
3. **Escalar por coordenadora** — cada uma executa o fluxo pelo próprio executável/GUI.
4. **Usar a agenda como gatilho** — eventos no Google Calendar com título `Status report-...` definem quais clientes processar no dia.
5. **Automatizar o Projeto Funcional** — ler a planilha do cliente, filtrar por status e montar tabelas nativas nos slides (concluídos, pendentes, em andamento).

---

## Fluxos de execução

### Fluxo principal (GUI — coordenadora)

```
Coordenadora abre a GUI
    ↓
Informa nome + data
    ↓
Busca coordenadora na aba Coord_Status_Report (email)
    ↓
Lê Google Calendar da coordenadora no dia
    ↓
Filtra eventos que começam com "Status report"
    ↓
Extrai código do cliente do título do evento
    ↓
Cruza com aba Clientes + usa ID completo do título do evento na capa
    ↓
Para cada cliente encontrado:
    ├── Copia template do Slides para pasta de saída (subpasta com data)
    ├── Substitui placeholders (capa, fechamento, quantidades)
    ├── Busca link da planilha de Projeto Funcional (aba Projetos_Funcionais)
    ├── Lê e filtra itens por status
    ├── Monta tabelas nos slides 6, 7 e 8
    └── Publica apresentação na pasta de saída
```

### Fluxo alternativo (CLI — agendamento diário)

```
poetry run python -m status_report.main
    ↓
Valida dia útil (seg–sex), salvo --force-run
    ↓
Lê aba Clientes filtrando por dia da semana + ativo
    ↓
Processa cada cliente da fila (mesmo pipeline de geração)
```

### Formato esperado do evento no Calendar

```
Status report-131-ID: 0078-25-HONORP SUPCON
```

O sistema extrai o código numérico do cliente (`131`) e cruza com a aba `Clientes`. O **ID completo na capa** (`{{CLIENTE_ID}}`) vem do **título do evento**, não da planilha de coordenadoras.

---

## Arquitetura

```
src/status_report/
├── configuracao.py              # Carrega .env em objeto Configuracoes
├── main.py                      # CLI (pipeline diário)
├── gui.py                       # Interface gráfica (tkinter)
│
├── dominio/
│   └── modelos.py               # ClienteFila, DadosRelatorio, ItemProjetoFuncional, etc.
│
├── infraestrutura/
│   ├── autenticacao_google.py   # Service account + DWD + APIs Google
│   ├── repositorio_planilha.py  # Leitura genérica de intervalos no Sheets
│   ├── repositorio_calendario.py# Eventos de Status Report no Calendar
│   ├── repositorio_drive.py     # Cópia, subpastas, links no Drive
│   ├── repositorio_apresentacao.py # replaceAllText no Slides
│   ├── repositorio_clientes.py  # Aba Clientes (cadastro centralizado)
│   ├── repositorio_indice_projetos.py # Aba Projetos_Funcionais (projeto → link)
│   ├── repositorio_projeto_funcional.py # Leitura da planilha PF (Sheets ou Excel)
│   └── repositorio_tabela_slide.py  # Criação/estilização de tabelas no Slides
│
├── aplicacao/
│   ├── fila_clientes.py         # Filtro por dia da semana (CLI)
│   ├── fila_clientes_calendario.py # Lookup coordenadora + match com Calendar
│   ├── pipeline_diario.py       # Orquestração CLI + _processar_cliente
│   ├── pipeline_coordenadora.py # Orquestração GUI
│   ├── projeto_funcional.py     # Agrupa itens por status (limite 12)
│   ├── render_projeto_funcional.py # Monta tabelas nos slides 6/7/8
│   └── renderizacao_relatorio.py # Agrega placeholders dos renderizadores
│
└── renderizadores/
    ├── protocolo.py             # Contrato RenderizadorSlide
    ├── registro.py              # Lista de renderizadores ativos
    ├── slide_capa.py            # Slide 1
    └── slide_fechamento.py      # Slide 17
```

Para incluir um novo slide com placeholders de texto, crie `renderizadores/<nome>.py` implementando `coletar_substituicoes` e registre em `renderizadores/registro.py`.

---

## Planilhas e abas utilizadas

### Planilha principal (`GOOGLE_SPREADSHEET_ID`)

Controle central com as abas abaixo.

#### Aba `Coord_Status_Report`

Cadastro **somente de coordenadoras**. Usada pela GUI para obter e-mail e validar se a coord está ativa.

| Coluna | Campo | Exemplo |
|--------|-------|---------|
| A | coordenadora | `Jordana` |
| B | ativo | `TRUE` |
| C | email | `jordana@ghr.com.br` |

Intervalo configurado: `GOOGLE_COORD_RANGE=Coord_Status_Report!A2:C`

#### Aba `Clientes`

Cadastro centralizado de clientes. Usada pelo CLI (fila do dia) e pela GUI (cruzamento com Calendar).

| Coluna | Campo | Exemplo |
|--------|-------|---------|
| A | codigo_cliente | `131` |
| B | nome_curto | `131 - HONORP` |
| C | cliente_id_completo | `131-ID: 0078-25 HONORP - SUPCON` |
| D | nome_pdf_customizado | (opcional) |
| E | ativo | `TRUE` |
| F | dias_semana | `SEG,TER,QUA,QUI` (vazio = todo dia útil; usado no CLI) |

**Regras:**
- `ativo = FALSE` ignora a linha.
- `nome_pdf_customizado` vazio → `Status Report - <nome_curto> - <data>`.
- Na **GUI**, o `{{CLIENTE_ID}}` da capa vem do **título do evento** no Calendar (ex.: `131-ID: 0078-25-HONORP SUPCON`).
- O **código do projeto** (ex.: `0078-25`) é extraído do ID (evento ou coluna C) para buscar a planilha de Projeto Funcional.

Intervalo configurado: `GOOGLE_CLIENTS_RANGE=Clientes!A2:F`

#### Aba `Projetos_Funcionais`

Índice que mapeia cada projeto ao link da sua planilha de Projeto Funcional.

| Coluna | Campo | Exemplo |
|--------|-------|---------|
| A | id_projeto | `ID: 0078-25-HONORP SUPCON` |
| B | link_planilha | `https://docs.google.com/spreadsheets/d/...` |

O casamento é feito pelo **código do projeto** (`0078-25`), não pelo código do cliente (`131`). Um mesmo cliente pode ter vários projetos.

Intervalo configurado: `GOOGLE_PROJECTS_INDEX_RANGE=Projetos_Funcionais!A1:B300`

#### Aba `Agenda da Semana` (futuro)

Reservada para extração de dados adicionais dos slides.

Intervalo configurado: `GOOGLE_DATA_RANGE=Agenda da Semana!A1:G200`

---

### Planilha de Projeto Funcional (por cliente)

Cada projeto tem sua própria planilha, linkada na aba `Projetos_Funcionais`. O arquivo pode ser:

- **Google Sheets nativo** — lido via Sheets API.
- **Excel (.xlsx) no Drive** — baixado via Drive API e lido com `openpyxl`.

A aba correta é detectada automaticamente pelo **cabeçalho** (linha com colunas `Status` e `Descrição`), independente do nome da aba (ex.: `COPEL`, `Projeto Funcional HONORP`).

#### Colunas lidas (mapeadas pelo nome do cabeçalho)

| Campo interno | Cabeçalho na planilha |
|---------------|----------------------|
| numero | `#` / `ID` |
| data_registro | `Data registro` |
| modulo | `Módulo` |
| funcao | `Função` / `Processo` |
| analista | `Analista` |
| descricao | `Descrição` |
| prioridade | `Prioridade` |
| status | `Status` |

Colunas extras (`Nível`, `Data Entrega`, `Avaliação`, etc.) são ignoradas.

#### Status reconhecidos

| Texto no status | Categoria |
|-----------------|-----------|
| contém `conclu` | Concluídos |
| contém `andamento` | Em andamento |
| contém `pendente` | Pendentes |

Exemplos reais: `50-CONCLUÍDO`, `20-EM ANDAMENTO`, `10-PENDENTE`.

**Limite de exibição:** 12 linhas por categoria no slide. O título mostra o **total real** (ex.: `Concluídos (58)`).

---

## Template Google Slides

### Slides com placeholders de texto

| Slide | Placeholders | Origem |
|-------|-------------|--------|
| 1 — Capa | `{{CLIENTE_ID}}`, `{{COORDENADORA}}`, `{{DATA}}` | Evento Calendar + `Coord_Status_Report` |
| 17 — Fechamento | `{{EMAIL_COORDENADORA}}`, `{{DATA}}` | `Coord_Status_Report` |

### Slides com tabelas dinâmicas (Projeto Funcional)

| Slide | Conteúdo | Placeholder no título |
|-------|----------|----------------------|
| 6 | Concluídos | `{{QTD_CONCLUIDOS}}` |
| 7 | Pendentes | `{{QTD_PENDENTES}}` |
| 8 | Em andamento | `{{QTD_EM_ANDAMENTO}}` |

**Títulos sugeridos no template:**
```
Projeto Funcional - Concluídos ({{QTD_CONCLUIDOS}})
Projeto Funcional - Pendentes ({{QTD_PENDENTES}})
Projeto Funcional - Em Andamento ({{QTD_EM_ANDAMENTO}})
```

As tabelas são criadas via Slides API (não são screenshots). O sistema remove imagens existentes no slide e insere uma tabela nativa com:
- Cabeçalho azul GHR, texto branco
- Linhas alternadas (zebra)
- Coluna Status colorida (verde / vermelho / laranja)

#### Colunas da tabela no slide

`#` | `Data` | `Módulo` | `Função/Processo` | `Analista` | `Descrição` | `Prioridade` | `Status`

---

## Saída no Google Drive

```
Pasta de saída (GOOGLE_OUTPUT_FOLDER_ID)
└── 2026-05-14/                    ← subpasta com a data do dia
    └── Status Report - 131 - GHR - 2026-05-14
```

A apresentação é salva como **Google Slides nativo** (não PDF/PPTX exportado), para evitar limitações de tamanho da API.

---

## Autenticação Google

O projeto usa uma **Service Account** com **Delegação em todo o domínio (DWD)** para agir em nome de um usuário da empresa (`GOOGLE_DELEGATED_USER`).

### APIs necessárias (Google Cloud Console)

- Google Sheets API
- Google Drive API
- Google Slides API
- Google Calendar API

### Escopos na delegação de domínio (Admin Console)

```
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/spreadsheets.readonly
https://www.googleapis.com/auth/presentations
https://www.googleapis.com/auth/calendar.readonly
```

### Compartilhamentos necessários

| Recurso | Permissão |
|---------|-----------|
| Planilha principal | Leitor (ou via DWD) |
| Template Slides | Editor |
| Pasta de saída (Shared Drive) | Editor |
| Planilhas de Projeto Funcional | Leitor (ou via DWD) |

> **Importante:** arquivos em Shared Drive são necessários para a service account criar/copiar arquivos. Contas pessoais (gmail.com) não funcionam por limitação de cota.

---

## Variáveis do `.env`

| Variável | Descrição |
|----------|-----------|
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Caminho do JSON da service account |
| `GOOGLE_SERVICE_ACCOUNT_EMAIL` | E-mail da service account |
| `GOOGLE_DELEGATED_USER` | Usuário da empresa impersonado via DWD (ex.: `pedro@ghr.com.br`) |
| `GOOGLE_SPREADSHEET_ID` | Planilha principal (`Controle_Super_Indice`) |
| `GOOGLE_TEMPLATE_PRESENTATION_ID` | ID do template no Google Slides |
| `GOOGLE_OUTPUT_FOLDER_ID` | Pasta de saída no Drive (Shared Drive) |
| `GOOGLE_COORD_RANGE` | Intervalo da aba `Coord_Status_Report` |
| `GOOGLE_CLIENTS_RANGE` | Intervalo da aba `Clientes` |
| `GOOGLE_DATA_RANGE` | Intervalo da aba `Agenda da Semana` |
| `GOOGLE_PROJECTS_INDEX_RANGE` | Intervalo da aba `Projetos_Funcionais` |
| `TIMEZONE` | Fuso horário (padrão: `America/Sao_Paulo`) |
| `RUN_ONLY_WEEKDAYS` | `true` para rodar apenas seg–sex |
| `DRY_RUN` | `true` para validar sem gerar arquivos |

---

## Como executar

### 1. Instalar dependências

```bash
poetry install
```

### 2. Configurar `.env`

Copie `.env.example` para `.env` e preencha os IDs.

### 3. Interface gráfica (coordenadora)

```bash
poetry run python -m status_report.gui
```

Na tela:
1. Digite o nome da coordenadora (exatamente como na planilha).
2. Informe a data (ou use o botão **Hoje**).
3. Clique em **Gerar Status Reports**.

### 4. CLI (agendamento / testes)

```bash
# Execução normal (respeita dia útil)
poetry run python -m status_report.main

# Forçar execução em fim de semana
poetry run python -m status_report.main --force-run

# Simular sem gerar arquivos
poetry run python -m status_report.main --dry-run

# Data específica
poetry run python -m status_report.main --date 2026-05-14
```

---

## Scripts de diagnóstico e teste

| Script | O que faz |
|--------|-----------|
| `scripts/verificar_pre_execucao.py` | Valida acessos (fila, template, pasta) |
| `scripts/listar_abas.py` | Lista abas da planilha principal |
| `scripts/inspecionar_indice_projetos.py` | Mostra conteúdo da aba `Projetos_Funcionais` |
| `scripts/inspecionar_template.py` | Lista slides e elementos do template |
| `scripts/testar_projeto_funcional.py` | Testa leitura + filtragem da planilha PF |
| `scripts/testar_slides_projeto.py` | Testa só a renderização das tabelas (gera cópia) |
| `scripts/diagnosticar_template.py` | Testa acesso e cópia do template |
| `scripts/mostrar_client_id.py` | Exibe Client ID para configurar DWD |

Exemplos:

```bash
poetry run python scripts/verificar_pre_execucao.py
poetry run python scripts/testar_projeto_funcional.py
poetry run python scripts/testar_slides_projeto.py
poetry run python scripts/inspecionar_indice_projetos.py
```

---

## Tratativas de erro (GUI)

| Situação | Comportamento |
|----------|---------------|
| Nome da coordenadora errado | Sugere nomes parecidos cadastrados na planilha |
| E-mail vazio na planilha | Aviso para preencher coluna G |
| Nenhum evento no Calendar | Aviso claro com a data consultada |
| Evento sem match na planilha | Explica formato esperado do título |
| Projeto não encontrado no índice | Gera capa/fechamento; tabelas PF ficam vazias |
| Falha na leitura da planilha PF | Gera o restante do slide; aviso no log |

---

## Agendamento automático (seg–sex)

Use o **Windows Task Scheduler** para rodar 1x ao dia:

```
poetry run python -m status_report.main
```

O código também valida internamente se é dia útil (`RUN_ONLY_WEEKDAYS=true`).

---

## Roadmap / próximas etapas

- [ ] Aba `Clientes` na planilha principal (código → dados do banco de dados)
- [ ] Slides adicionais alimentados por MongoDB/API
- [ ] Empacotamento com PyInstaller (`.exe` por coordenadora)
- [ ] Suporte a múltiplos projetos por cliente no mesmo dia (um arquivo por projeto)

---

## Dependências principais

| Pacote | Uso |
|--------|-----|
| `google-api-python-client` | APIs Google (Sheets, Drive, Slides, Calendar) |
| `google-auth` | Autenticação service account + DWD |
| `openpyxl` | Leitura de planilhas Excel (.xlsx) no Drive |
| `python-dotenv` | Carregamento do `.env` |
| `tzdata` | Fuso horário |
| `python-pptx` (dev) | Inspeção local de templates `.pptx` |
