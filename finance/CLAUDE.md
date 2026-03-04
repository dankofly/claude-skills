# Finance Skills - Claude Code Guidance

This guide covers the finance skill and its Python automation tools.

## Finance Skills Overview

**Available Skills:**
1. **financial-analyst/** - Financial statement analysis, ratio analysis, DCF valuation, budgeting, forecasting (4 Python tools)
2. **austrian-tax-advisor/** - Austrian tax calculations (ESt, KöSt, USt, KESt, ImmoESt, Krypto), Rechtsformvergleich, Steueroptimierung + Web-Chatbot (7 Python tools + FastAPI chatbot)

**Total Tools:** 11 Python automation tools, 8 knowledge bases, 9 templates

## Python Automation Tools

### 1. Ratio Calculator (`financial-analyst/scripts/ratio_calculator.py`)

**Purpose:** Calculate and interpret financial ratios from statement data

**Features:**
- Profitability ratios (ROE, ROA, Gross/Operating/Net Margin)
- Liquidity ratios (Current, Quick, Cash)
- Leverage ratios (Debt-to-Equity, Interest Coverage, DSCR)
- Efficiency ratios (Asset/Inventory/Receivables Turnover, DSO)
- Valuation ratios (P/E, P/B, P/S, EV/EBITDA, PEG)
- Built-in interpretation and benchmarking

**Usage:**
```bash
python financial-analyst/scripts/ratio_calculator.py financial_data.json
python financial-analyst/scripts/ratio_calculator.py financial_data.json --format json
```

### 2. DCF Valuation (`financial-analyst/scripts/dcf_valuation.py`)

**Purpose:** Discounted Cash Flow enterprise and equity valuation

**Features:**
- Revenue and cash flow projections
- WACC calculation (CAPM-based)
- Terminal value (perpetuity growth and exit multiple methods)
- Enterprise and equity value derivation
- Two-way sensitivity analysis
- No external dependencies (uses math/statistics)

**Usage:**
```bash
python financial-analyst/scripts/dcf_valuation.py valuation_data.json
python financial-analyst/scripts/dcf_valuation.py valuation_data.json --format json
```

### 3. Budget Variance Analyzer (`financial-analyst/scripts/budget_variance_analyzer.py`)

**Purpose:** Analyze actual vs budget vs prior year performance

**Features:**
- Variance calculation (actual vs budget, actual vs prior year)
- Materiality threshold filtering
- Favorable/unfavorable classification
- Department and category breakdown

**Usage:**
```bash
python financial-analyst/scripts/budget_variance_analyzer.py budget_data.json
python financial-analyst/scripts/budget_variance_analyzer.py budget_data.json --format json
```

### 4. Forecast Builder (`financial-analyst/scripts/forecast_builder.py`)

**Purpose:** Driver-based revenue forecasting and cash flow projection

**Features:**
- Driver-based revenue forecast model
- 13-week cash flow projection
- Scenario modeling (base/bull/bear)
- Trend analysis from historical data

**Usage:**
```bash
python financial-analyst/scripts/forecast_builder.py forecast_data.json
python financial-analyst/scripts/forecast_builder.py forecast_data.json --format json
```

## Quality Standards

**All finance Python tools must:**
- Use standard library only (math, statistics, json, argparse)
- Support both JSON and human-readable output via `--format` flag
- Provide clear error messages for invalid input
- Return appropriate exit codes
- Process files locally (no API calls)
- Include argparse CLI with `--help` support

### Austrian Tax Advisor Tools (`austrian-tax-advisor/scripts/`)

**5-7. Einkommensteuer, KöSt, USt, Sachbezug, IFB, ImmoESt, Krypto**

All 7 tools follow the same pattern:
```bash
python austrian-tax-advisor/scripts/<script>.py input.json
python austrian-tax-advisor/scripts/<script>.py input.json --format json
echo '{"key": "value"}' | python austrian-tax-advisor/scripts/<script>.py -
```

| Script | Purpose |
|---|---|
| `einkommensteuer_rechner.py` | ESt 2026 (7 Stufen, Absetzbeträge, Familienbonus) |
| `koerperschaftsteuer_rechner.py` | KöSt 23%, KESt, Rechtsformvergleich |
| `umsatzsteuer_rechner.py` | USt-Zahllast, Kleinunternehmerregelung |
| `sachbezug_rechner.py` | PKW-Sachbezug, steuerfreie Benefits |
| `investitionsfreibetrag_rechner.py` | IFB 20%/22%, Forschungsprämie 14% |
| `immobilienertragssteuer_rechner.py` | ImmoESt 30%, Alt-/Neuvermögen |
| `krypto_steuer_rechner.py` | KESt 27,5% Krypto, Portfolio-Tracking |

**Web-Chatbot** (Claude API + Tool Use):
```bash
cd austrian-tax-advisor/chatbot && pip install -r requirements.txt && uvicorn app:app --port 8000
```

## Related Skills

- **C-Level:** Strategic financial decision-making -> `../c-level-advisor/`
- **Business & Growth:** Revenue operations, sales metrics -> `../business-growth/`
- **Product Team:** Budget allocation, RICE scoring -> `../product-team/`

---

**Last Updated:** March 2026
**Skills Deployed:** 2/2 finance skills production-ready
**Total Tools:** 11 Python automation tools + 1 Web-Chatbot
