# Amazon PPC Auditor

> A privacy-first diagnostic engine for Amazon Sponsored Products. Upload a Search Term Report and get a prioritized list of wasted spend, cannibalized traffic, loss-making campaigns and safe scaling opportunities, with no Seller Central API access required.

![Python](https://img.shields.io/badge/python-3.12-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![uv](https://img.shields.io/badge/deps-uv-6340ac)
![Ruff](https://img.shields.io/badge/lint-ruff-d7ff64)
![Tests](https://img.shields.io/badge/tests-pytest-0a9edc)

### 🚀 [Try the live app → ppcx-app.streamlit.app](https://ppcx-app.streamlit.app/)

---

## Overview

Most Amazon sellers lose a large share of their PPC budget to search terms that never convert, to the same query bidding against itself across match types, and to campaigns that run below break-even. Finding these by hand in a Search Term Report with thousands of rows is slow and error-prone.

**Amazon PPC Auditor** automates that review:

- **No API, no store authorization.** Sellers export a standard report from Seller Central and upload it.
- **In-memory computation.** Report data is processed in the session and never persisted.
- **Margin-aware.** Every recommendation is measured against the seller's own break-even ACoS, not a generic benchmark.
- **Bilingual.** Accepts Chinese and English report headers (legacy and current Amazon schemas). The UI and Excel export are available in 中文 and English.

## Documentation

| Audience | Document |
| --- | --- |
| Sellers and operators | [User Guide (English)](docs/user-guide.md) · [用户指南 (中文)](docs/user-guide.zh-CN.md) |
| Analysts | [Audit Methodology](docs/methodology.md): every formula, threshold and default |
| Developers | [Developer Guide](docs/developer-guide.md): architecture, setup, testing, deployment |

## Features

| Module | What it finds | Engine method |
| --- | --- | --- |
| 🛑 **Zero-sale bleeders** | Search terms spending without converting, caught by two detectors: a *slow bleed* (clicks above a CVR-derived threshold for the campaign) and a *fast hemorrhage* (spend above 2× break-even CPA). Supports a strategic whitelist for brand and defensive terms. | `extract_zero_sale_terms` |
| ⚔️ **Match-type cannibalization** | The same customer search term served by multiple ad groups or match types. Variants are ranked by ACoS and CPC, and the spend on losing variants is quantified. | `detect_match_type_cannibalization` |
| 💸 **Structural loss** | Campaigns whose realized ACoS exceeds break-even, with *capital lost* compared with allowable spend and a graded recommendation (Investigate / Deflate bids / Cap budget). | `evaluate_campaign_breakeven_health` |
| 🚀 **Scaling opportunities** | Proven terms (min. orders) running safely below break-even ACoS, ranked by estimated gross profit, with match-type-aware next steps. | `extract_top_performing_terms` |
| 🧱 **Portfolio fragility** | Concentration risk, meaning the share of total spend held by the top-N search terms. | `assess_portfolio_fragility` |

Results appear in an interactive dashboard and can be downloaded as a localized, multi-sheet **Excel audit report**.

## How it works

```
 Seller Central export (.xlsx / .csv)
              │
              ▼
 ┌──────────────────────────────┐
 │ AmazonSPSchema               │  header normalization (ZH/EN, full-width
 │ backend/schema.py            │  brackets, legacy daily reports), type
 └──────────────┬───────────────┘  coercion, friendly validation errors
                ▼
 ┌──────────────────────────────┐
 │ AmazonPPCAuditor             │  1. drop rows inside the 7-day attribution lag
 │ backend/auditor/             │  2. aggregate once on a 5-dimensional key
 │   amazon_ppc_auditor.py      │     (campaign, ad group, match type,
 └──────────────┬───────────────┘      targeting, search term)
                │                  3. run each audit module on shared state
                ▼
 ┌──────────────────────────────┐
 │ Streamlit dashboard + Excel  │  ui/audit_dashboard.py, ui/i18n.py
 └──────────────────────────────┘
```

**Attribution lag.** Amazon attributes orders up to 7 days after a click. The auditor excludes the most recent `lag_days` of data from conversion-based decisions, so it doesn't flag terms whose sales haven't been reported yet.

## Input data

Export a **Sponsored Products → Search Term** report from the Amazon Ads console (Excel or CSV) with **Time unit: Daily**. The auditor drops the most recent 7 days to allow for attribution lag, so a *Summary* report, where every row ends on the last day, leaves nothing to audit. See the [user guide](docs/user-guide.md#2-export-your-search-term-report) for step-by-step export instructions. These columns are required. Any of the listed aliases is accepted, and matching ignores case and whitespace.

| Internal key | English header | Chinese header |
| --- | --- | --- |
| `start_date` | Start Date / Date | 开始日期 / 日期 |
| `end_date` | End Date *(optional for daily reports)* | 结束日期 |
| `campaign_name` | Campaign Name | 广告活动名称 |
| `ad_group_name` | Ad Group Name | 广告组名称 / 广告组合名称 |
| `targeting` | Targeting | 投放 |
| `match_type` | Match Type | 匹配类型 |
| `customer_search_term` | Customer Search Term | 客户搜索词 |
| `impressions` | Impressions | 展示量 |
| `clicks` | Clicks | 点击量 |
| `spend` | Spend | 花费 |
| `orders_7d` | 7 Day Total Orders (#) | 7天总订单数(#) |
| `total_sales_7d` | 7 Day Total Sales | 7天总销售额 / 七天总销售额 |

For the most reliable results, use at least **14 days** of data. The app warns you when the window is shorter.

## Quick start

**Hosted:** open https://ppcx-app.streamlit.app/ and upload a report. Nothing to install.

**Run locally:** you need Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

```bash
uv run streamlit run dashboards/ppc_audit_report.py
```

Then open http://localhost:8501.

### Docker

```bash
docker compose up --build
```

### Configuration

| Setting | Where | Purpose |
| --- | --- | --- |
| `SUPABASE_URL`, `SUPABASE_KEY` | `.streamlit/secrets.toml` | *Optional* anonymous usage telemetry. When unset, telemetry is disabled and the app runs normally |

## Project structure

```
├── dashboards/
│   ├── ppc_audit_report.py     # Production Streamlit entrypoint
│   ├── app.py                  # Experimental CPC bid-optimizer demo
│   └── ...                     # Other prototypes and visualizations
├── docs/                       # User guide (EN/ZH), methodology, developer guide
├── src/
│   ├── backend/
│   │   ├── auditor/amazon_ppc_auditor.py   # Core audit engine
│   │   ├── schema.py                       # Report normalization & validation
│   │   ├── data_prepoc.py                  # Synthetic data + Bayesian smoothing helpers
│   │   └── telemetry.py                    # Fail-safe usage telemetry
│   └── ui/
│       ├── audit_dashboard.py  # Dashboard tabs + Excel export
│       ├── contract.py         # Backend column → UI label mapping
│       └── i18n.py             # zh / en translations
├── tests/                      # pytest unit tests
├── Dockerfile
└── docker-compose.yaml
```

## Development

Install dev dependencies (pytest, ruff, pre-commit) and the git hooks:

```bash
uv sync --group dev
```

```bash
uv run pre-commit install
```

Run the test suite with coverage:

```bash
uv run pytest --cov=src --cov-report=term-missing
```

Lint and format:

```bash
uv run ruff check . --fix && uv run ruff format .
```

The tests use small, hand-built reports (see `tests/conftest.py`). Every expected number can be worked out by hand from the fixture. See the [Developer Guide](docs/developer-guide.md) for architecture, conventions, and how to add new audit modules.

## Deployment

Production runs on **Streamlit Community Cloud** at https://ppcx-app.streamlit.app/. It's served from `dashboards/ppc_audit_report.py` on `main` and redeploys automatically on every push. Optional secrets (`SUPABASE_URL` / `SUPABASE_KEY`) are configured in the app settings. A Docker image is also provided for self-hosting. Details are in the [Developer Guide](docs/developer-guide.md#8-deployment).

## Roadmap

- [x] Search-term audit engine and bilingual dashboard
- [x] Localized Excel audit export
- [ ] Bid optimization: profit-maximizing CPC recommendations under a budget constraint (SLSQP with Bayesian-smoothed click elasticity). A prototype is in `dashboards/app.py`.
- [ ] Sponsored Brands / Sponsored Display report support
- [ ] Bulk-sheet export for one-click negative keyword uploads

## Privacy

Uploaded reports are processed entirely in memory for the duration of the session. Nothing is written to disk or sent to third parties. Optional telemetry records product events (page views, report exports with the selected margin, and feedback the user chooses to submit) under an anonymous session ID. Telemetry never includes report contents.

## License

Copyright © 2026 Jianhong Chen. All rights reserved.
