# PDF Table Extractor

API para extrair tabelas de arquivos PDF e exportá-las em CSV ou Excel. Usa `pdfplumber` com três estratégias de detecção de grade (linhas, texto, mista) e escolhe a que produzir o resultado mais consistente por página.

## Arquitetura

```
src/
  core/        modelos de domínio, exceções e o algoritmo de extração (sem dependência de framework)
  db/          SQLite: schema, conexão e repositório
  services/    orquestração de jobs e exportação (CSV/XLSX)
  api/         rotas FastAPI e injeção de dependências via app.state
  main.py      composição da aplicação e lifespan
static/        frontend (HTML/CSS/JS puro, sem build step)
```

Cada job de upload é processado em background (`BackgroundTasks`) e passa pelos estados `queued -> processing -> completed | failed`. Tabelas extraídas são persistidas como JSON no SQLite junto com um score de confiança (0 a 1) calculado a partir da consistência do número de colunas e da densidade de células preenchidas.

## Requisitos

- Python 3.11+

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Execução

```bash
uvicorn src.main:app --reload
```

A aplicação sobe em `http://localhost:8000`. A interface web fica na raiz; a documentação OpenAPI, em `/docs`.

Via Docker:

```bash
docker compose up --build
```

## API

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/upload` | Envia um PDF (`multipart/form-data`, campo `file`); retorna `job_id` |
| GET | `/api/job/{job_id}/status` | Status do job |
| GET | `/api/job/{job_id}/tables` | Job com as tabelas extraídas |
| GET | `/api/job/{job_id}/export/csv?table_id=` | Exporta uma tabela específica em CSV |
| GET | `/api/job/{job_id}/export/xlsx` | Exporta todas as tabelas do job em um Excel (uma aba por tabela) |
| GET | `/api/history` | Lista todos os jobs |
| DELETE | `/api/job/{job_id}` | Remove o job, suas tabelas e o arquivo armazenado |

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes de API geram PDFs de exemplo em memória com `reportlab`, sem depender de arquivos fixos no repositório. `tests/conftest.py` isola cada teste com diretórios de upload e banco de dados próprios em `tmp_path`.

## Decisões e limitações

- A detecção de tabelas roda inteiramente sobre o texto e as linhas vetoriais do PDF (via `pdfplumber`); PDFs escaneados como imagem não têm texto extraível e não são suportados sem OCR.
- Motores adicionais (`camelot`, `tabula-py`) foram deixados de fora deliberadamente: dependem de Ghostscript/JVM no sistema, o que fragiliza a instalação sem ganho evidente sobre as três variantes de estratégia já usadas.
- O processamento em background usa `BackgroundTasks` do FastAPI, adequado para o volume de um único worker; para paralelismo real entre múltiplos workers, trocar por uma fila (Redis/RQ ou Celery) sem alterar a camada de domínio.

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
