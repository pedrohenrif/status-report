# Projeto de Automacao - Status Report (Python)

## O que foi entendido do video

Observacao: a analise foi feita por amostragem visual de frames do video (sem transcricao de audio). Mesmo assim, o fluxo demonstrado ficou claro:

1. Existe uma planilha principal no Google Sheets (`Controle_Super_Indice`) com abas como:
   - `Status Report`
   - `Entregaveis`
   - `Cronograma`
   - `Comercial`
   - `Agenda da Semana`
2. Essa planilha funciona como indice e fonte de dados operacionais (clientes, codigos, atividades, responsaveis, agenda e acompanhamento).
3. No Google Drive existe uma pasta com historico de arquivos tipo `Status Report - ... .pptx` por data.
4. Os arquivos de status sao abertos no Google Slides para revisao/atualizacao de conteudo (capa, equipes e papeis, controle de horas, alvos etc.).
5. O processo aparenta depender de consolidacao manual de dados da planilha para montar/atualizar o material final.

## E possivel automatizar?

Sim, e viavel automatizar com Python.

### Viabilidade tecnica

- **Acesso ao Drive**: viavel com Google Drive API (listar pastas, buscar template, criar copia, exportar PDF).
- **Leitura de dados**: viavel com Google Sheets API (ler abas/intervalos).
- **Atualizacao do modelo**:
  - Melhor caminho: usar um **template no Google Slides** e preencher com Slides API.
  - Alternativa: usar `python-pptx` localmente para gerar `.pptx` e depois converter.
- **Saida em PDF**: viavel exportando o Slides para PDF via Drive API.
- **Agendamento**: viavel com tarefa diaria/semanal no Windows Task Scheduler ou GitHub Actions.

### Pontos de atencao

- Definir claramente **quais campos** da planilha alimentam cada secao do relatorio.
- Padronizar template com placeholders (ex.: `{{CLIENTE}}`, `{{PERIODO}}`, `{{HORAS_TOTAL}}`).
- Tratar permissao/compartilhamento no Drive (service account precisa de acesso as pastas).
- O consumo final sera pelas coordenadoras a partir de uma pasta de saida no Drive.

## Arquitetura sugerida (Python)

1. **Extractor**
   - Conecta no Google Sheets.
   - Le dados necessarios de abas definidas.
   - Normaliza em um objeto unico (`report_data`).
2. **Renderer**
   - Faz copia do template no Drive.
   - Atualiza placeholders e tabelas no Google Slides.
3. **Exporter**
   - Exporta para PDF.
   - Salva em pasta de destino no Drive.
4. **Publisher**
   - Publica os PDFs finais na pasta de saida do Drive para consumo das coordenadoras.

## Passo a passo de implementacao

## 1) Preparar projeto Python

1. Criar ambiente virtual.
2. Instalar dependencias:
   - `google-api-python-client`
   - `google-auth`
   - `google-auth-oauthlib`
   - `google-auth-httplib2`
   - `pydantic` (opcional para validacao)
   - `python-dotenv`
3. Estrutura sugerida:

```text
status_report/
  src/
    config.py
    google_clients.py
    sheets_reader.py
    slides_writer.py
    drive_exporter.py
    pipeline.py
  templates/
  output/
  .env
  requirements.txt
```

## 2) Configurar Google Cloud

1. Criar projeto no Google Cloud.
2. Ativar APIs:
   - Google Drive API
   - Google Sheets API
   - Google Slides API
3. Criar credenciais (service account).
4. Baixar JSON da service account.
5. Compartilhar:
   - pasta do Drive (templates/saida)
   - planilha de origem
   com o email da service account.

### Variaveis de ambiente que devem ser preenchidas

- `GOOGLE_SERVICE_ACCOUNT_FILE`: caminho local do JSON da service account.
- `GOOGLE_SPREADSHEET_ID`: ID da planilha principal.
- `GOOGLE_TEMPLATE_PRESENTATION_ID`: ID do template no Google Slides.
- `GOOGLE_OUTPUT_FOLDER_ID`: ID da pasta no Drive onde as coordenadoras vao consumir os PDFs.
- `GOOGLE_CLIENT_QUEUE_RANGE`: intervalo da aba/fila com clientes que rodam no dia (padrao `Status Report!A2:F`).
- `GOOGLE_DATA_RANGE`: intervalo para extracao de dados do relatorio (padrao `Status Report!A1:Z500`).
- `RUN_ONLY_WEEKDAYS`: `true` para seg-sex.
- `DRY_RUN`: `true` para validar sem publicar PDF.

## 3) Definir mapeamento de dados

Criar um documento de mapeamento:

- `Aba/Coluna -> Campo interno -> Slide/Placeholder`

Exemplo:
- `Status Report!B2 -> cliente_nome -> {{CLIENTE}}`
- `Controle_Horas!F10 -> horas_total -> {{HORAS_TOTAL}}`
- `Agenda da Semana!A:H -> agenda_tabela -> slide Agenda`

Esse passo e o mais importante para evitar retrabalho.

## 4) Montar o template de apresentacao

1. Criar um arquivo modelo no Google Slides.
2. Inserir placeholders textuais padrao.
3. Manter layout fixo para facilitar substituicao.
4. Guardar `template_presentation_id` no `.env`.

## 5) Implementar leitura da planilha

1. Ler os ranges necessarios com Sheets API.
2. Transformar em estrutura Python:
   - campos simples
   - listas/tabelas
3. Validar obrigatorios (cliente, periodo, principais metricas).

## 6) Implementar preenchimento do Slides

1. Copiar template.
2. Executar `batchUpdate` para substituir placeholders.
3. Atualizar blocos de tabela (quando necessario, por texto formatado ou tabela do proprio Slides).
4. Salvar `presentation_id` gerado.

## 7) Exportar PDF no Drive

1. Chamar exportacao do arquivo para MIME `application/pdf`.
2. Gravar no Drive em pasta de destino com nome padrao:
   - `Status Report - <cliente> - <periodo>.pdf`
3. Retornar link compartilhavel.

## 8) Criar pipeline diario (seg-sex) com loop por cliente

Orquestrar em uma funcao principal:

1. Verificar dia da semana (rodar apenas segunda a sexta, exceto quando `force_run=true`).
2. Ler da planilha quais clientes precisam de Status Report no dia.
3. Para cada cliente da lista, executar:
   - extracao de dados
   - renderizacao do Slides
   - exportacao para PDF
   - salvamento na pasta final do Drive
4. Registrar resultado por cliente (sucesso/falha + link do PDF).

## 9) Testes e homologacao

1. Rodar com 1 cliente piloto.
2. Comparar PDF gerado com modelo manual atual.
3. Ajustar mapeamento/layout.
4. So depois escalar para todos os clientes.

## 10) Operacao recorrente

1. Agendar execucao de segunda a sexta (uma vez ao dia).
2. Gerar logs de sucesso/erro.
3. Criar pasta de historico por mes.
4. Definir responsavel de contingencia.

## MVP recomendado (rapido e seguro)

Para entregar valor rapido:

1. Escolher 1 tipo de relatorio (ex.: um cliente/unidade).
2. Preencher apenas:
   - capa
   - controle de horas
   - agenda da semana
3. Gerar PDF automaticamente no Drive.

Com MVP validado, ampliar para os demais blocos.

## Proximos passos imediatos

1. Confirmar qual arquivo e o **template oficial** (Slides ou PDF).
2. Confirmar quais campos sao obrigatorios na versao 1.
3. Eu posso montar em seguida o esqueleto do codigo Python (`src/`) com a pipeline pronta para plugar IDs reais.
