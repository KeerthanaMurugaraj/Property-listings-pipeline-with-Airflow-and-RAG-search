# Property listings pipeline with Airflow and RAG search

A small end-to-end data project: rental listings from three estate agencies are collected every day, cleaned and merged in SQL, and made searchable in plain language. Apache Airflow orchestrates every step.

The agencies are simulated (`sources/`), so the project runs without any external account. No real website is scraped.

## What it does

```
listings_daily (every day at 06:00 UTC)
  extract ─┬─ agency A: CSV file
           ├─ agency B: JSON API (fails on the first call, to show retries)
           └─ agency C: XML feed
  load_raw -> normalize -> validate -> deduplicate -> build_listings
                                                          │
                                         asset "core_listings" updated
                                                          ▼
listings_index (runs when the asset is updated)
  index_listings -> evaluate_index -> publish_index
```

| Step | What happens | Where |
|---|---|---|
| Extract | Each source is copied untouched into `data/raw/<source>/<date>/` | `listings/extract.py` |
| Load | Raw files become raw tables in DuckDB | `listings/load.py` |
| Normalize | Three formats, languages and units become one set of columns | `sql/normalize_agency_*.sql` |
| Validate | Bad rows go to a quarantine view; too many bad rows stop the run | `sql/validate.sql` |
| Deduplicate | The same property from two agencies becomes one row | `sql/dedupe.sql` |
| Build | One row per property with its current state and price history | `sql/listings.sql` |
| Index | Only new or changed listings are embedded and written to LanceDB | `listings/index.py` |
| Evaluate | Test questions are run against the new index version | `rag/evaluate.py` |
| Publish | Only a version that passes becomes the one that searches use | `rag/store.py` |

Design choices:

- **ELT in SQL.** Python moves data; every transformation is a SQL file in `sql/`.
- **Safe re-runs.** Every table is written per day (delete the day, insert the day), so running a day twice gives the same result.
- **Incremental embedding.** Each listing has a fingerprint of its text. Unchanged listings are never embedded again.
- **Quality gate.** A new index version is searched only after it passes `data/eval/golden.jsonl`.
- **Two DAGs joined by an asset.** The warehouse DAG does not know the index DAG exists.

## Run it with Docker

Needs Docker Desktop.

```bash
docker compose up --build -d
```

Open http://localhost:8088, switch on `listings_index`, then `listings_daily`. The daily run starts by itself and then triggers the index run.

```bash
# search the published index
docker compose exec scheduler python /opt/airflow/app/main.py "furnished studio with parking"

# load earlier days
docker compose exec scheduler airflow backfill create --dag-id listings_daily --from-date 2026-10-01 --to-date 2026-10-09

# stop (add -v to also delete the data)
docker compose down
```

The Compose file starts Postgres, the three Airflow services (API server, scheduler, DAG processor) and the simulated agency API. The passwords and the secret in it are placeholders for local use only.

## Run it without Docker

Needs conda.

```bash
conda create -n listings python=3.13 -y
conda activate listings
pip install "apache-airflow==3.3.2" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.13.txt"
pip install -r requirements.txt

source scripts/env.sh        # from the project root, in every new terminal
airflow db migrate           # once: creates Airflow's own database in airflow_home/
python -m sources.api        # terminal 1: the simulated agency API
airflow standalone           # terminal 2: Airflow, UI at http://localhost:8080
```

Useful commands:

```bash
airflow dags test listings_daily 2026-10-10          # run one day without the scheduler
airflow dags test listings_index
python -m listings.warehouse "SELECT * FROM core.listings LIMIT 5"
python main.py "house with a garden"
python main.py "house with a garden" --answer        # needs ANTHROPIC_API_KEY
pytest
```

## Layout

| Path | Contents |
|---|---|
| `dags/listings_pipeline.py` | The two DAGs |
| `listings/` | Pipeline logic called by the tasks |
| `sql/` | One SELECT per file |
| `rag/` | Embeddings, vector store, evaluation, answer generation |
| `sources/` | The simulated agencies |
| `tests/` | DAG structure tests and SQL tests |
| `data/eval/golden.jsonl` | Test questions for the index |
| `Dockerfile`, `docker-compose.yaml` | The container setup |

## Configuration

| Variable | Meaning | Default |
|---|---|---|
| `LISTINGS_DATA_DIR` | Where raw files, the warehouse and the index are stored | `data/` |
| `AIRFLOW_CONN_AGENCY_B` | Address of Agency B's API, as an Airflow connection | set in `scripts/env.sh` and `docker-compose.yaml` |
| `ANTHROPIC_API_KEY` | Only for `main.py --answer` | not set |

## Stack

Apache Airflow 3.3, DuckDB, LanceDB, fastembed (`BAAI/bge-small-en-v1.5`), Postgres (Airflow metadata in Docker), Claude (optional answer generation).
