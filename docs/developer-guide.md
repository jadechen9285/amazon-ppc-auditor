# Developer Guide

This guide is for contributors working on **Amazon PPC Auditor**. For how the audit rules work, see [methodology.md](methodology.md). For the end-user workflow, see the [user guide](user-guide.md).

---

## Contents

1. [Architecture](#1-architecture)
2. [Local setup](#2-local-setup)
3. [Codebase tour](#3-codebase-tour)
4. [Common tasks](#4-common-tasks)
5. [Testing](#5-testing)
6. [Code style](#6-code-style)
7. [Configuration and secrets](#7-configuration-and-secrets)
8. [Deployment](#8-deployment)
9. [Known limitations](#9-known-limitations)

---

## 1. Architecture

The production app is a single Streamlit script backed by a pure-pandas engine. The backend never imports Streamlit, except `telemetry.py`, which reads `st.secrets`.

```
dashboards/ppc_audit_report.py           ← Streamlit entrypoint (one script run per interaction)
 │
 ├─ language toggle  → st.session_state['lang']        (ui/i18n.py)
 ├─ sidebar          → margin slider, file uploader (≤ 15 MB)
 │
 ├─ pd.read_excel / pd.read_csv (CSV delimiter sniffing: , \t ;)
 ├─ AmazonSPSchema.validate_and_normalize(raw_df)     (backend/schema.py)
 │     └─ SchemaValidationError → heuristic "wrong report type" messages
 ├─ AmazonPPCAuditor(clean_df)                        (backend/auditor/amazon_ppc_auditor.py)
 ├─ generate_excel_report(auditor, margin)            (ui/audit_dashboard.py)
 └─ render_audit_dashboard(auditor, margin)           (ui/audit_dashboard.py)
       ├─ hero metrics
       ├─ tabs: Emergency Stops · Structural Risks · Scaling Opportunities
       └─ feedback form → insert_telemetry_row        (backend/telemetry.py)
```

Design principles:

- **One aggregation, many audits.** `AmazonPPCAuditor.__init__` computes the mature slice and the micro aggregation once. Audit methods are read-only views over that state.
- **One internal schema.** Everything after `AmazonSPSchema` uses the snake_case keys in `REQUIRED_INTERNAL_KEYS`. Raw Amazon headers never reach the engine.
- **Presentation is separate.** Engine methods return DataFrames and dicts. Labels, translations and Excel column names are applied in `ui/`.
- **Telemetry fails safe.** Telemetry errors never reach the user.

## 2. Local setup

Prerequisites: **Python 3.12** and **[uv](https://docs.astral.sh/uv/)**.

```bash
uv sync --group dev
```

```bash
uv run pre-commit install
```

```bash
uv run streamlit run dashboards/ppc_audit_report.py
```

The app runs at http://localhost:8501. No login or invite code is required.

The `backend` and `ui` packages are importable because the project is installed into the venv as a package (`[tool.hatch.build.targets.wheel] packages = ["src/backend", "src/ui"]`). Pytest also adds `src/` to `sys.path` through `pythonpath = ["src"]`.

> `pyproject.toml` sets the Tsinghua PyPI mirror as the default index. If installs are slow outside mainland China, override it for a single command, e.g. `UV_DEFAULT_INDEX=https://pypi.org/simple uv sync`.

## 3. Codebase tour

| Path | Responsibility |
| --- | --- |
| `dashboards/ppc_audit_report.py` | **Production entrypoint.** Routing, gate, upload, error heuristics, landing page with a sample-format table |
| `src/backend/schema.py` | `AmazonSPSchema`: alias map, header normalization, validation, type coercion |
| `src/backend/auditor/amazon_ppc_auditor.py` | `AmazonPPCAuditor`: maturity window, micro aggregation, five audit methods |
| `src/backend/telemetry.py` | `insert_telemetry_row`: fire-and-forget POST to Supabase |
| `src/backend/data_prepoc.py` | Experimental: synthetic data generator and Bayesian smoothing helpers for the bid optimizer |
| `src/ui/audit_dashboard.py` | Dashboard rendering and `generate_excel_report` |
| `src/ui/i18n.py` | `TEXTS` dictionary (`key → {'zh', 'en'}`) and `t(key, **kwargs)` |
| `src/ui/contract.py` | `UIContract`: backend column key → translated label (`col_<key>`) |
| `dashboards/app.py` | Experimental SLSQP bid-optimizer demo with `streamlit-authenticator` |
| `dashboards/demo_phase_0_v0.py`, `cpc_euqation_vis.py` | Early prototypes and visualizations |
| `prompts/` | Domain and role prompt notes used during product design |
| `tests/` | pytest suite (see [Testing](#5-testing)) |

## 4. Common tasks

### Support a new report header

Add the alias to the right set in `AmazonSPSchema.ALIAS_MAP`. Matching ignores case and spaces, so `'7 Day Total Sales'` covers `'7 day total sales'` and `'7DayTotalSales'`. Then add a case to `tests/test_schema.py`.

### Add a required column

1. Add the key to `ALIAS_MAP` and `REQUIRED_INTERNAL_KEYS`.
2. Add type coercion in `validate_and_normalize` if the column is numeric or a date.
3. Add the column to `make_row` in `tests/conftest.py`.
4. Update the column table in the [README](../README.md#input-data) and the landing-page sample in `ppc_audit_report.py`.

### Add an audit module

1. Add a method to `AmazonPPCAuditor` that reads `self.df_mature` / `self.df_micro`. Don't re-aggregate the raw data. When the data is empty or doesn't qualify, return the same shape as a real result (an empty DataFrame, or a dict with zeroed metrics), so the UI never has to special-case it.
2. Keep action labels bilingual (`'中文 (English)'`), matching the existing methods.
3. Render it in `ui/audit_dashboard.py` (a new `_render_tab_*` function and an entry in `st.tabs`).
4. If it should be exported, add a sheet in `generate_excel_report`. Add new output columns to `UIContract.get_excel_map()` and `col_<key>` translations to `TEXTS`.
5. Write tests with hand-checkable numbers. Document the formula in [methodology.md](methodology.md).

### Add or change UI text

Add a key to `TEXTS` in `src/ui/i18n.py` with **both** `zh` and `en`. `tests/test_i18n_contract.py` fails if either language is missing. Use `{placeholders}` for dynamic values and pass them as `t('key', name=value)`.

## 5. Testing

```bash
uv run pytest
```

```bash
uv run pytest --cov=src --cov-report=term-missing
```

| File | Covers |
| --- | --- |
| `tests/conftest.py` | Shared builders and fixtures |
| `test_schema.py` | Header aliases (EN/ZH), daily-report handling, validation errors, coercion |
| `test_auditor.py` | Maturity window, aggregation, and every audit method, including edge cases |
| `test_data_preproc.py` | Bayesian smoothing, elasticity clipping, synthetic generator |
| `test_i18n_contract.py` | Translation lookup and fallback, completeness of `TEXTS` and the Excel map |
| `test_telemetry.py` | Secrets handling, payload shape, network failures |
| `test_excel_report.py` | Workbook sheets, localization, empty sections |

Conventions:

- **Build data with `make_row` / `make_clean_df`.** `make_clean_df` adds a zero-spend *anchor* row dated `2026-08-31`, which sets the maturity cutoff to `2026-08-24`. Rows default to `2026-08-01`, which is mature.
- **Use numbers you can check by hand.** Pick values so the expected result is obvious (e.g. CVR = 1/32 → threshold 48), and put the arithmetic in a comment.
- **Streamlit is isolated.** An autouse fixture replaces `st.session_state` with a dict-like fake and sets `st.secrets = {}`. Tests never touch real session state or secrets, and they never make network calls. Use the `session_state` fixture to set `lang`.
- **The Streamlit render functions aren't unit-tested.** Check UI changes by running the app.

## 6. Code style

- [Ruff](https://docs.astral.sh/ruff/) handles linting and formatting. The config is in `pyproject.toml`: line length 100, single quotes, rules `E W F I UP`.
- Pre-commit runs `ruff check --fix` and `ruff format` on every commit.
- Use snake_case DataFrame columns. Engine outputs keep the internal key names, and renaming happens only in `ui/`.

```bash
uv run ruff check . --fix && uv run ruff format .
```

## 7. Configuration and secrets

| Name | Source | Used by | Notes |
| --- | --- | --- | --- |
| `SUPABASE_URL` | `st.secrets` | `telemetry.py` | Optional. Telemetry is off when missing |
| `SUPABASE_KEY` | `st.secrets` | `telemetry.py` | Optional. Telemetry is off when missing |
| `BASE_DATA_PATH`, `REAL_DATA_PATH`, `SYNTHETIC_DATA_PATH` | `.env` (see `.env.template`) | notebooks and experiments | Not used by the production app |

For local secrets, create `.streamlit/secrets.toml` (it's gitignored):

```toml
SUPABASE_URL = "https://<project>.supabase.co"
SUPABASE_KEY = "<anon-key>"
```

### Telemetry table

`insert_telemetry_row` POSTs to `{SUPABASE_URL}/rest/v1/app_telemetry` with a 2-second timeout:

| Column | Type | Example |
| --- | --- | --- |
| `created_at` | timestamptz | ISO-8601 UTC |
| `event_type` | text | `PAGE_VIEW`, `ACTION_CLICK`, `FEEDBACK` |
| `sentiment` | int, nullable | thumbs feedback (0/1) |
| `details` | text | `[Session: <uuid>] Exported Global Excel \| Margin: 30%` |

Telemetry must never include report contents.

## 8. Deployment

### Streamlit Community Cloud (production)

The live app is **https://open-ppcx.streamlit.app/**.

| Setting | Value |
| --- | --- |
| Repository / branch | `jadechen9285/amazon-ppc-auditor` / `main` |
| Main file path | `dashboards/ppc_audit_report.py` |
| Python version | 3.12 |
| Secrets | Optional: `SUPABASE_URL`, `SUPABASE_KEY` (in *App settings → Secrets*, TOML format) |

Community Cloud redeploys automatically when `main` changes. If the platform needs a `requirements.txt`, generate one with:

```bash
bash scripts/generate_req_text.sh
```

`.streamlit/config.toml` holds the theme, hides error tracebacks (`showErrorDetails = false`), and caps the upload size at 30 MB. The app enforces its own 15 MB limit.

### Docker

```bash
docker compose up --build
```

The image installs only runtime dependencies (`uv sync --frozen --no-dev`), copies `src/`, `dashboards/` and `.streamlit/`, and serves `dashboards/ppc_audit_report.py` on port 8501.

### Release checklist

1. `uv run pytest` and `uv run ruff check .` pass.
2. Upload a real Daily Search Term Report (EN and ZH headers) in a local run.
3. Update [methodology.md](methodology.md) if any audit rule changed.
4. Merge to `main`. Streamlit Cloud redeploys on its own.

## 9. Known limitations

- **Summary reports return no findings.** Every row ends on the report's last day, which falls inside the 7-day lag (see [methodology §1.2](methodology.md#12-attribution-lag-maturity-window)). The user guide asks for Daily reports.
- **Sales headers with a currency symbol**, such as `7 Day Total Sales ($)`, aren't in `ALIAS_MAP` yet.
- **The language of missing-column errors varies.** The label comes from an unordered set, so it can be Chinese or English.
- **Amounts always show `$`**, whatever the report currency.
- **The strategic whitelist** exists in the engine but isn't exposed in the UI.
- **`dashboards/app.py` is demo-only.** It contains a hard-coded credential hash and cookie key. Don't deploy it as is.
