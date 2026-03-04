#!/usr/bin/env python3
"""
Austrian Corporate Tax Calculator 2026

Calculates KöSt, KESt on distributions, total tax burden, and compares
legal forms (GmbH vs FlexCo vs Einzelunternehmen).

Usage:
    python koerperschaftsteuer_rechner.py input.json
    python koerperschaftsteuer_rechner.py input.json --format json
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple


KOEST_RATE = 0.23
KEST_RATE = 0.275
MINDEST_KOEST_GMBH = 500.00
MINDEST_KOEST_FLEXCO = 500.00
MINDEST_KOEST_AG = 3_500.00
VERLUST_VORTRAGS_GRENZE = 0.75

# ESt brackets for Einzelunternehmen comparison
EST_BRACKETS: List[Tuple[float, float, float]] = [
    (0.00, 13_539.00, 0.00),
    (13_539.01, 21_992.00, 0.20),
    (21_992.01, 36_458.00, 0.30),
    (36_458.01, 70_365.00, 0.40),
    (70_365.01, 104_859.00, 0.48),
    (104_859.01, 1_000_000.00, 0.50),
    (1_000_000.01, float("inf"), 0.55),
]

EST_BASE_TAX: List[float] = [
    0.00, 0.00, 1_690.60, 5_830.40,
    19_393.20, 35_950.32, 483_520.82,
]


class CorporateTaxCalculator:
    """Calculate Austrian corporate tax (KöSt + KESt) for 2026."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.profit: float = float(data.get("gewinn", 0))
        self.share_capital: float = float(data.get("stammkapital", 10_000))
        self.distribution_pct: float = float(data.get("ausschuettung_prozent", 100))
        self.legal_form: str = data.get("rechtsform", "gmbh").lower()
        self.loss_carryforward: float = float(data.get("verlustvortraege", 0))

    def calculate_est(self, taxable_income: float) -> float:
        """Calculate progressive ESt for Einzelunternehmen."""
        if taxable_income <= 0:
            return 0.0
        for i, (lower, upper, rate) in enumerate(EST_BRACKETS):
            if taxable_income <= upper:
                return round(EST_BASE_TAX[i] + (taxable_income - (lower - 0.01 if i > 0 else 0)) * rate, 2)
        return 0.0

    def calculate_gewinnfreibetrag(self, profit: float) -> float:
        """Calculate Gewinnfreibetrag for Einzelunternehmen."""
        if profit <= 0:
            return 0.0
        if profit <= 33_000:
            return round(profit * 0.15, 2)
        if profit >= 583_000:
            return 46_400.00
        base = 33_000 * 0.15
        remaining = min(profit, 583_000) - 33_000
        max_remaining = 583_000 - 33_000
        additional = (46_400 - base) * (remaining / max_remaining)
        return round(base + additional, 2)

    def get_mindest_koest(self) -> float:
        """Return Mindestkörperschaftsteuer based on legal form."""
        if self.legal_form == "ag":
            return MINDEST_KOEST_AG
        return MINDEST_KOEST_GMBH

    def calculate_corporate(self, profit: float, legal_form: str, dist_pct: float) -> Dict[str, Any]:
        """Calculate corporate tax for GmbH/FlexCo."""
        # Loss carryforward (max 75% of profit)
        usable_loss = min(self.loss_carryforward, profit * VERLUST_VORTRAGS_GRENZE)
        taxable_profit = max(profit - usable_loss, 0)

        koest = round(taxable_profit * KOEST_RATE, 2)
        mindest = MINDEST_KOEST_GMBH if legal_form != "ag" else MINDEST_KOEST_AG
        koest_final = max(koest, mindest) if profit > 0 else mindest

        profit_after_koest = max(profit - koest_final, 0)
        distribution = round(profit_after_koest * dist_pct / 100, 2)
        kest = round(distribution * KEST_RATE, 2)
        net_shareholder = round(distribution - kest, 2)
        retained = round(profit_after_koest - distribution, 2)
        total_tax = round(koest_final + kest, 2)
        effective_rate = round(total_tax / profit * 100, 2) if profit > 0 else 0.0

        return {
            "rechtsform": legal_form.upper(),
            "gewinn": profit,
            "verlustvortraege_genutzt": round(usable_loss, 2),
            "steuerpflichtiger_gewinn": round(taxable_profit, 2),
            "koerperschaftsteuer": koest_final,
            "mindestkoest": mindest,
            "mindestkoest_angewendet": koest_final == mindest and koest < mindest,
            "gewinn_nach_koest": round(profit_after_koest, 2),
            "ausschuettung": distribution,
            "ausschuettung_prozent": dist_pct,
            "kest_auf_ausschuettung": kest,
            "netto_gesellschafter": net_shareholder,
            "thesaurierung": retained,
            "gesamtsteuerbelastung": total_tax,
            "effektive_steuerquote": f"{effective_rate:.2f} %",
        }

    def calculate_einzelunternehmen(self, profit: float) -> Dict[str, Any]:
        """Calculate tax for Einzelunternehmen (sole proprietorship)."""
        gfb = self.calculate_gewinnfreibetrag(profit)
        taxable = max(profit - gfb, 0)
        est = self.calculate_est(taxable)
        net = round(profit - est, 2)
        effective_rate = round(est / profit * 100, 2) if profit > 0 else 0.0

        return {
            "rechtsform": "Einzelunternehmen",
            "gewinn": profit,
            "gewinnfreibetrag": gfb,
            "zu_versteuerndes_einkommen": round(taxable, 2),
            "einkommensteuer": est,
            "netto": net,
            "gesamtsteuerbelastung": est,
            "effektive_steuerquote": f"{effective_rate:.2f} %",
        }

    def calculate(self) -> Dict[str, Any]:
        """Run the full calculation with legal form comparison."""
        # Main calculation for selected legal form
        if self.legal_form == "einzelunternehmen":
            main_result = self.calculate_einzelunternehmen(self.profit)
        else:
            main_result = self.calculate_corporate(self.profit, self.legal_form, self.distribution_pct)

        # Comparison across all legal forms
        gmbh = self.calculate_corporate(self.profit, "gmbh", self.distribution_pct)
        flexco = self.calculate_corporate(self.profit, "flexco", self.distribution_pct)
        eu = self.calculate_einzelunternehmen(self.profit)

        comparison = [
            {
                "rechtsform": "GmbH",
                "steuerbelastung": gmbh["gesamtsteuerbelastung"],
                "netto": gmbh.get("netto_gesellschafter", 0),
                "effektive_quote": gmbh["effektive_steuerquote"],
            },
            {
                "rechtsform": "FlexCo",
                "steuerbelastung": flexco["gesamtsteuerbelastung"],
                "netto": flexco.get("netto_gesellschafter", 0),
                "effektive_quote": flexco["effektive_steuerquote"],
            },
            {
                "rechtsform": "Einzelunternehmen",
                "steuerbelastung": eu["gesamtsteuerbelastung"],
                "netto": eu["netto"],
                "effektive_quote": eu["effektive_steuerquote"],
            },
        ]

        # Determine best option
        best = min(comparison, key=lambda x: x["steuerbelastung"])

        # Thesaurierung vs Ausschüttung comparison
        thesaurierung = self.calculate_corporate(self.profit, self.legal_form, 0)
        vollausschuettung = self.calculate_corporate(self.profit, self.legal_form, 100)

        return {
            "berechnung": main_result,
            "rechtsformvergleich": comparison,
            "empfehlung": f"{best['rechtsform']} ist bei diesem Gewinn steuerlich am günstigsten ({best['effektive_quote']}).",
            "thesaurierung_vs_ausschuettung": {
                "vollthesaurierung": {
                    "steuerbelastung": thesaurierung["gesamtsteuerbelastung"],
                    "effektive_quote": thesaurierung["effektive_steuerquote"],
                },
                "vollausschuettung": {
                    "steuerbelastung": vollausschuettung["gesamtsteuerbelastung"],
                    "effektive_quote": vollausschuettung["effektive_steuerquote"],
                },
            },
        }


def format_human_readable(result: Dict[str, Any]) -> str:
    """Format calculation results for human reading."""
    main = result["berechnung"]
    lines = [
        "=" * 60,
        "  KÖRPERSCHAFTSTEUER-BERECHNUNG 2026",
        "=" * 60,
        "",
        f"  Rechtsform:                   {main['rechtsform']}",
        f"  Gewinn:                       EUR {main['gewinn']:>12,.2f}",
    ]

    if "koerperschaftsteuer" in main:
        lines.extend([
            f"  KöSt (23 %):                  EUR {main['koerperschaftsteuer']:>12,.2f}",
            f"  Gewinn nach KöSt:             EUR {main['gewinn_nach_koest']:>12,.2f}",
            f"  Ausschüttung ({main['ausschuettung_prozent']:.0f} %):          EUR {main['ausschuettung']:>12,.2f}",
            f"  KESt (27,5 %):                EUR {main['kest_auf_ausschuettung']:>12,.2f}",
            f"  Netto Gesellschafter:         EUR {main['netto_gesellschafter']:>12,.2f}",
            f"  Thesaurierung:                EUR {main['thesaurierung']:>12,.2f}",
        ])
    else:
        lines.extend([
            f"  Gewinnfreibetrag:             EUR {main['gewinnfreibetrag']:>12,.2f}",
            f"  Zu verst. Einkommen:          EUR {main['zu_versteuerndes_einkommen']:>12,.2f}",
            f"  Einkommensteuer:              EUR {main['einkommensteuer']:>12,.2f}",
            f"  Netto:                        EUR {main['netto']:>12,.2f}",
        ])

    lines.extend([
        "",
        "-" * 60,
        f"  GESAMTSTEUERBELASTUNG:        EUR {main['gesamtsteuerbelastung']:>12,.2f}",
        f"  Effektive Steuerquote:        {main['effektive_steuerquote']}",
        "-" * 60,
        "",
        "  RECHTSFORMVERGLEICH:",
        f"  {'Rechtsform':<25} {'Steuer':>12} {'Netto':>12} {'Quote':>10}",
        "  " + "-" * 57,
    ])

    for c in result["rechtsformvergleich"]:
        lines.append(
            f"  {c['rechtsform']:<25} EUR {c['steuerbelastung']:>8,.2f} EUR {c['netto']:>8,.2f} {c['effektive_quote']:>8}"
        )

    lines.extend([
        "",
        f"  {result['empfehlung']}",
        "",
        "  THESAURIERUNG vs AUSSCHÜTTUNG:",
        f"  Vollthesaurierung:   {result['thesaurierung_vs_ausschuettung']['vollthesaurierung']['effektive_quote']}",
        f"  Vollausschüttung:    {result['thesaurierung_vs_ausschuettung']['vollausschuettung']['effektive_quote']}",
        "",
        "  Hinweis: Keine Steuerberatung. Alle Berechnungen sind",
        "  Richtwerte.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Österreichischer Körperschaftsteuer-Rechner 2026"
    )
    parser.add_argument("input_file", help="JSON-Datei mit Unternehmensdaten (oder '-' für stdin)")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Ausgabeformat")
    args = parser.parse_args()

    try:
        if args.input_file == "-":
            data = json.load(sys.stdin)
        else:
            with open(args.input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
    except FileNotFoundError:
        print(f"Fehler: Datei '{args.input_file}' nicht gefunden.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Fehler: Ungültiges JSON — {e}", file=sys.stderr)
        sys.exit(1)

    if "gewinn" not in data:
        print("Fehler: 'gewinn' ist erforderlich.", file=sys.stderr)
        sys.exit(1)

    calculator = CorporateTaxCalculator(data)
    result = calculator.calculate()

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_human_readable(result))


if __name__ == "__main__":
    main()
