# Audit Methodology

This document defines every calculation the auditor makes. It's written for analysts who want to check the logic and for developers changing it. The implementation is in [`src/backend/auditor/amazon_ppc_auditor.py`](../src/backend/auditor/amazon_ppc_auditor.py). Each rule here is covered by a test in [`tests/test_auditor.py`](../tests/test_auditor.py).

**Notation.** *m* is the break-even margin set in the sidebar (default 0.30). The 7-day attribution metrics are written *orders* and *sales*.

---

## 1. Data preparation

### 1.1 Normalization

[`AmazonSPSchema.validate_and_normalize`](../src/backend/schema.py) maps raw headers to internal keys. Matching ignores case and spaces and treats full-width brackets `（）` as `()`. It also:

- Copies `start_date` into `end_date` when the report only has one date column (daily reports in some locales).
- Converts numeric columns to numbers, turning unparseable values and blanks into `0`.
- Fills an empty `targeting` with `AUTO_TARGET` (auto campaigns).
- Parses both date columns, turning invalid dates into `NaT`.

### 1.2 Attribution-lag maturity window

Amazon attributes orders up to 7 days after a click, so recent rows understate conversions.

```
max_date    = max(end_date)
cutoff_date = max_date − lag_days          (lag_days = 7)
mature rows = rows where end_date ≤ cutoff_date
```

All conversion-based modules (bleeders, winners, break-even, cannibalization) use mature rows only. Portfolio fragility uses **all** rows, because spend is known immediately.

> **Consequence:** a *Summary* report puts every row's `end_date` on the last day of the report, so there are no mature rows and those modules return empty results. Users must upload *Daily* reports.

Two values come from this step:

```
ad_duration_day  = (max_date − start_date) in days        # age of each row
observation_days = max(1, cutoff_date − min(mature start_date))
```

### 1.3 Micro aggregation

Mature rows are grouped **once** on a five-part key, and every module reuses the result:

```
(campaign_name, ad_group_name, match_type, targeting, customer_search_term)
```

The aggregates are `impressions`, `clicks`, `spend`, `orders_7d` and `total_sales_7d` (summed), plus `ad_duration_day` (mean).

---

## 2. Zero-sale bleeders: `extract_zero_sale_terms`

Two independent detectors run on micro rows with `orders = 0`.

### 2.1 Campaign baselines (from mature rows)

```
CVR_c = orders_c / clicks_c        (0.05 if the campaign has no clicks)
AOV_c = sales_c / orders_c         (global AOV if the campaign has no orders)
global AOV = Σ sales / max(Σ orders, 1)     (30.0 if the account has no sales)
```

### 2.2 Slow bleed: Chronic Non-Converter

```
max_tolerated_clicks = max( ceil( (1 / CVR_c) × click_multiplier ), absolute_click_floor )
duration_threshold   = min( ad_duration_day_threshold, max ad_duration_day in data )

flag if  clicks ≥ max_tolerated_clicks  AND  ad_duration_day ≥ duration_threshold
```

| Parameter | Default | Meaning |
| --- | --- | --- |
| `click_multiplier` | 1.5 | How many "expected clicks per order" a term may use before it's flagged |
| `absolute_click_floor` | 5 | Never flag on fewer clicks than this |
| `ad_duration_day_threshold` | 14 | Minimum age in days. It's lowered automatically when the report is shorter |

*Worked example:* Camp A has 160 mature clicks and 5 orders, so CVR is 1/32. The limit is ceil(32 × 1.5) = **48 clicks**. A term with 60 clicks, no orders, and an age of 30 days is flagged.

### 2.3 Fast bleed: High Velocity Spend

```
catastrophic_limit = AOV_c × m × 2          # twice the break-even CPA
flag if spend ≥ catastrophic_limit
```

When a term trips both detectors, it gets the High Velocity label.

### 2.4 Strategic whitelist

Terms in `strategic_whitelist` are matched after trimming and lowercasing. They're relabelled **Strategic Hold** and not removed. This is an engine parameter only; the UI doesn't expose it yet.

Output is sorted by action, then spend (descending).

---

## 3. Match-type cannibalization: `detect_match_type_cannibalization`

1. Keep micro rows with `spend ≥ min_spend_filter` (default $5).
2. Find search terms that appear in more than one row (different campaign, ad group, match type or targeting).
3. For each term, rank its rows by **ACoS ascending, then CPC ascending**:
   ```
   ACoS = spend / sales   (∞ when sales = 0)
   CPC  = spend / clicks  (0 when clicks = 0)
   ```
4. Rank 1 is the **Winner**. All others are **Losers**.

```
total_cannibalized_spend = Σ spend of Loser rows
impacted_search_terms    = number of overlapping terms
```

---

## 4. Campaign break-even health: `evaluate_campaign_breakeven_health`

Campaign totals come from mature rows. Only campaigns with `total_spend ≥ min_spend_threshold` (default $20) are assessed.

```
realized_ACoS   = total_spend / total_sales      (∞ when sales = 0)
allowable_spend = total_sales × m
capital_lost    = max(0, total_spend − allowable_spend)
```

Campaigns with `realized_ACoS > m` are reported. The action is the first rule that matches:

| Order | Condition | Action |
| --- | --- | --- |
| 1 | `total_sales = 0` | Investigate: inject negatives |
| 2 | `realized_ACoS > 2m` | Deflate: lower base bids |
| 3 | `realized_ACoS > m` | Cap Budget: reduce daily budget |

Outputs: `total_capital_lost`, `unprofitable_campaign_count`, `observation_window_days`, and the sorted list of campaigns.

---

## 5. Scaling opportunities: `extract_top_performing_terms`

```
keep micro rows with orders ≥ min_orders (default 3) and ACoS < m
gross_profit = sales × m − spend
```

| Normalized match type | Action |
| --- | --- |
| `EXACT` | Evaluate bid/budget increase |
| `BROAD`, `PHRASE`, `AUTO` | Consider Exact extraction |
| anything else | Consider scaling traffic |

Sorted by `gross_profit`, descending.

---

## 6. Portfolio fragility: `assess_portfolio_fragility`

Uses **all** rows, mature or not.

```
concentration_ratio = spend of top-N search terms / total spend      (N = 10)
is_fragile          = concentration_ratio > risk_threshold           (0.40)
```

---

## 7. Dashboard headline metrics

| Metric | Formula |
| --- | --- |
| Est. Recoverable Loss | Σ bleeder spend + `total_cannibalized_spend` |
| Unprofitable Campaigns | `unprofitable_campaign_count` |
| Traffic Concentration Risk | `concentration_ratio` |

---

## 8. Experimental: bid optimization

[`src/backend/data_prepoc.py`](../src/backend/data_prepoc.py) and the [`dashboards/app.py`](../dashboards/app.py) prototype are the start of a CPC optimizer. They aren't part of the production audit.

- **Bayesian smoothing of conversion metrics** (`extract_financial_state`): local RPC and CVR are pulled toward the account average with weight *w = clicks / (clicks + half_life)*, so true value = *w* × local + (1 − *w*) × global.
- **Click elasticity** (`extract_price_elasticity`): β = Δlog(clicks) / Δlog(CPC) between consecutive days, clipped to [0.01, 1]. The median per target is then smoothed toward a prior of 0.5 in the same way.
- **Optimizer** (prototype): predicted clicks = clicks × (new CPC / CPC)^β. SLSQP maximizes Σ(sales × margin − spend) under the current total budget.
