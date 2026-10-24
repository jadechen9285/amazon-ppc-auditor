# User Guide

**English** · [中文](user-guide.zh-CN.md)

This guide explains how to audit your Amazon Sponsored Products (SP) campaigns with **Amazon PPC Auditor** and how to act on the results.

**Live app:** https://ppcx-app.streamlit.app/

---

## Contents

1. [Before you start](#1-before-you-start)
2. [Export your Search Term Report](#2-export-your-search-term-report)
3. [Set your break-even margin](#3-set-your-break-even-margin)
4. [Upload and run the audit](#4-upload-and-run-the-audit)
5. [Read the results](#5-read-the-results)
6. [Export the Excel report](#6-export-the-excel-report)
7. [Troubleshooting](#7-troubleshooting)
8. [FAQ](#8-faq)

---

## 1. Before you start

You need:

- **Access to the Amazon Ads console** (Seller Central → Advertising) for the account you want to audit.
- **Your product margin**, i.e. what's left of the selling price after product cost and Amazon fees, before advertising. See [step 3](#3-set-your-break-even-margin).

No store authorization or API connection is needed. You upload a file you exported yourself.

## 2. Export your Search Term Report

1. In the Amazon Ads console, open **Measurement & Reporting → Sponsored ads reports** and click **Create report**.
2. Set the options:

   | Option | Value |
   | --- | --- |
   | Ad product | **Sponsored Products** |
   | Report category | Search term |
   | **Time unit** | **Daily** ⚠️ |
   | Report period | **The last 30 days** (14 days minimum) |
   | File format | Excel (.xlsx) or CSV |

3. Run the report and download it once it's ready.

> ⚠️ **Choose "Daily", not "Summary".** Amazon keeps attributing orders for up to 7 days after a click, so the auditor ignores the most recent 7 days. A Summary report puts the whole period on one row ending today, which leaves nothing to analyse.

**Don't edit the file.** Keep Amazon's original column names, in English or Chinese. The app recognises both. The file must be **15 MB or smaller**. If yours is bigger, export a shorter period.

## 3. Set your break-even margin

The **Break-even Margin (Target ACoS)** slider in the sidebar is the most important setting. Every recommendation is measured against it.

It's the highest ACoS you can run on a sale without losing money:

```
break-even margin = (selling price − product cost − FBA fee − referral fee − other costs) ÷ selling price
```

*Example:* a product sells for $40 and costs $12 to make, with a $6 FBA fee and a $6 referral fee. The margin is (40 − 12 − 6 − 6) ÷ 40 = **40 %**. An ad sale with ACoS above 40 % loses money.

If your products have different margins, use a blended average. The default is 30 %, and the slider goes from 10 % to 80 %.

## 4. Upload and run the audit

1. Open the app and pick **English** or **中文** at the top of the sidebar.
2. Set the break-even margin.
3. Upload your report with **Upload Search Term Report**.

The audit runs straight away. A banner shows how many days the report covers:

- 📅 **14 days or more:** there's enough data, so you can rely on the results.
- ⚠️ **Under 14 days:** results are still shown but less reliable. Be careful before pausing anything.

You can change the margin at any time and the results update straight away.

## 5. Read the results

### Headline metrics

| Metric | Meaning |
| --- | --- |
| 🚨 **Est. Recoverable Loss** | Spend on zero-sale search terms plus spend lost to cannibalization. You can save this by taking the actions below. |
| 📉 **Unprofitable Campaigns** | The number of campaigns whose actual ACoS is above your break-even margin. |
| 🏗️ **Traffic Concentration Risk** | The share of total spend that goes to your top 10 search terms. Above **40 %** the account is fragile: a single competitor raising bids can cut your orders sharply. |

### Tab 1: 🛑 Emergency Stops

**Zero-Sale Bleeders** are search terms that cost money but never converted. Each one is labelled with the reason:

| Label | Why it was flagged | Suggested action |
| --- | --- | --- |
| 🚨 **High Velocity Spend** | Spent more than twice what one order is worth to you (average order value × margin × 2) with no sale | Add it as a **negative exact** keyword now, or cut the bid sharply |
| ⏳ **Chronic Non-Converter** | Got more clicks than the campaign normally needs to make a sale (the *Max Tolerated Clicks* column), over at least 14 days, with no sale | Add it as a negative exact keyword |

The click allowance is set per campaign. A campaign that converts 1 click in 20 gets a higher allowance than one that converts 1 in 5, so slow-converting categories aren't flagged too early.

**Match-Type Cannibalization** lists search terms that several of your own ad groups bid on. They compete with each other and push up your CPC. The most efficient version is marked **Winner** (lowest ACoS, then lowest CPC). The others are marked **Loser**. Keep the winner, and lower bids on the losers or add the term as a negative there.

### Tab 2: 💸 Structural Risks

This lists campaigns that run above your break-even margin over the observation window. **Capital Lost** is the spend beyond what the sales could pay for:

```
allowable spend = sales × break-even margin
capital lost    = actual spend − allowable spend
```

*Example:* with a 30 % margin, $100 in sales covers $30 of ad spend. If the campaign spent $50, it lost $20 of net profit.

| Diagnostic action | When | What to do |
| --- | --- | --- |
| **Investigate** | Spent money with zero sales | Check its search terms and add negatives |
| **Deflate** | ACoS above twice your margin | Lower bids across the campaign |
| **Cap Budget** | ACoS somewhat above your margin | Reduce the daily budget to keep only the most efficient traffic |

Only campaigns with at least $20 of spend are assessed. In the bubble chart, a larger bubble means more capital lost.

### Tab 3: 🚀 Scaling Opportunities

These are proven search terms with at least 3 orders and ACoS below your margin, ranked by **Est. Gross Profit** (sales × margin − spend).

| Current match type | Suggested action |
| --- | --- |
| **Exact** | Raise the bid or budget gradually |
| **Broad / Phrase / Auto** | Move it into its own Exact-match campaign |

> **Peel & Stick rule:** when you move a term out, **don't pause the original right away.** First lower its bid by 30–50 %. Let the new Exact campaign run for 7–14 days, then add the term as a negative in the original campaign. This keeps the term's sales history intact.

## 6. Export the Excel report

Click **Export Full Audit Report (Excel)** in the sidebar. The workbook is in the language you selected and has up to four sheets:

| Sheet | Contents |
| --- | --- |
| Bleeders | Zero-sale terms with diagnosis reason, clicks, threshold and spend |
| Cannibalization | Overlapping terms with Winner/Loser status |
| Structural Loss | Unprofitable campaigns with ACoS, allowable spend and capital lost |
| Winners | Scaling opportunities with action, orders, ACoS and estimated gross profit |

A sheet is left out when it has no findings.

## 7. Troubleshooting

| Message or symptom | Cause | Fix |
| --- | --- | --- |
| **Wrong Report: Brand Analytics (ABA)** | You uploaded a Brand Analytics search term report | Download the Sponsored Products search term report from the Ads console |
| **Wrong Report: Campaign / Advertised Product** | The report type isn't *Search term* | Recreate the report and pick **Search term** |
| **Sponsored Brands not supported** | You uploaded a Sponsored Brands report | Only Sponsored Products is supported for now |
| **Missing required columns** | Columns were renamed or deleted, or this is a different report | Re-export and upload the file unchanged |
| **File too large** | The file is over 15 MB | Export a shorter period (14–30 days) |
| Everything shows $0 or empty | You exported a **Summary** report, or the report covers 7 days or fewer | Export a **Daily** report covering 14–30 days |

## 8. FAQ

**Is my data stored?**
No. Your report is processed in memory during your session and isn't saved. Anonymous usage events (page views, exports, and feedback you choose to send) are collected to improve the product. They never include the contents of your report.

**Why are the last 7 days ignored?**
Amazon keeps attributing orders for up to 7 days after a click. A term that looks like it has no sales today may still get orders credited. Skipping that window avoids flagging good keywords.

**Does the app change my campaigns?**
No. It's read-only and gives recommendations only. You decide what to do in the Ads console.

**Which marketplaces and currencies are supported?**
Any marketplace whose Sponsored Products Search Term Report uses the standard English or Chinese column names. Amounts are shown with a `$` sign but use your report's currency.

**How do I report a bug or request a feature?**
Use the **Product Feedback** form at the bottom of the results page.
