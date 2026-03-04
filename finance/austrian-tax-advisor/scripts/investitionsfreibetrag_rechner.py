#!/usr/bin/env python3
"""
Austrian Investment Allowance Calculator 2026

Calculates IFB (20%/22% eco), Forschungsprämie (14%),
and Gewinnfreibetrag with eligibility checks.

Usage:
    python investitionsfreibetrag_rechner.py input.json
    python investitionsfreibetrag_rechner.py input.json --format json
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple


IFB_STANDARD_RATE = 0.20
IFB_OEKO_RATE = 0.22
IFB_MAX_COST_BASE = 1_000_000.00
FORSCHUNGSPRAEMIE_RATE = 0.14
GWG_GRENZE = 1_000.00

# ESt brackets for tax saving estimate
EST_BRACKETS: List[Tuple[float, float, float]] = [
    (0.00, 13_539.00, 0.00),
    (13_539.01, 21_992.00, 0.20),
    (21_992.01, 36_458.00, 0.30),
    (36_458.01, 70_365.00, 0.40),
    (70_365.01, 104_859.00, 0.48),
    (104_859.01, 1_000_000.00, 0.50),
    (1_000_000.01, float("inf"), 0.55),
]

# Categories that are excluded from IFB
EXCLUDED_CATEGORIES = {
    "grundstueck": "Grundstücke sind vom IFB ausgeschlossen",
    "gebaeude": "Gebäude sind vom IFB ausgeschlossen",
    "pkw_verbrenner": "PKW mit Verbrennungsmotor sind vom IFB ausgeschlossen",
    "gwg": "Geringwertige Wirtschaftsguter (bis EUR 1.000) sind ausgeschlossen",
    "gebraucht": "Gebrauchte Wirtschaftsgüter sind vom IFB ausgeschlossen",
    "fossil": "Anlagen mit fossilen Energieträgern sind ausgeschlossen",
}


class InvestmentAllowanceCalculator:
    """Calculate Austrian IFB, Forschungsprämie, and GFB for 2026."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.investments: List[Dict[str, Any]] = data.get("investitionen", [])
        self.profit: float = float(data.get("gewinn", 0))
        self.research_expenses: float = float(data.get("forschungsaufwendungen", 0))

    def get_marginal_rate(self, income: float) -> float:
        """Return marginal tax rate for a given income."""
        for lower, upper, rate in EST_BRACKETS:
            if income <= upper:
                return rate
        return 0.55

    def check_ifb_eligibility(self, investment: Dict[str, Any]) -> Tuple[bool, float, str]:
        """Check if an investment qualifies for IFB."""
        category = investment.get("kategorie", "standard").lower()
        amount = float(investment.get("betrag", 0))

        # Check exclusions
        if category in EXCLUDED_CATEGORIES:
            return False, 0.0, EXCLUDED_CATEGORIES[category]

        # GWG check by amount
        if amount <= GWG_GRENZE and category != "oeko":
            return False, 0.0, f"Betrag bis EUR {GWG_GRENZE:,.0f} (GWG -- Sofortabschreibung)"

        # Determine rate
        if category == "oeko":
            return True, IFB_OEKO_RATE, "Ökologische Investition (22 %)"
        else:
            return True, IFB_STANDARD_RATE, "Standard-IFB (20 %)"

    def calculate_gewinnfreibetrag(self) -> Dict[str, Any]:
        """Calculate Gewinnfreibetrag."""
        if self.profit <= 0:
            return {
                "gewinn": self.profit,
                "grundfreibetrag": 0.0,
                "investitionsbedingter_gfb": 0.0,
                "gesamt_gfb": 0.0,
            }

        # Grundfreibetrag: 15% of profit up to EUR 33,000
        grund_basis = min(self.profit, 33_000)
        grundfreibetrag = round(grund_basis * 0.15, 2)

        # Investitionsbedingter GFB for profit above EUR 33,000
        if self.profit > 33_000:
            if self.profit >= 583_000:
                gesamt = 46_400.00
            else:
                remaining = self.profit - 33_000
                max_remaining = 583_000 - 33_000
                additional = (46_400 - grundfreibetrag) * (remaining / max_remaining)
                gesamt = round(grundfreibetrag + additional, 2)
            inv_gfb = round(gesamt - grundfreibetrag, 2)
        else:
            inv_gfb = 0.0
            gesamt = grundfreibetrag

        return {
            "gewinn": self.profit,
            "grundfreibetrag": grundfreibetrag,
            "investitionsbedingter_gfb": inv_gfb,
            "gesamt_gfb": gesamt,
            "hinweis": "Grundfreibetrag wird automatisch gewährt (keine Investition nötig).",
        }

    def calculate(self) -> Dict[str, Any]:
        """Run the full calculation."""
        details = []
        total_investments = 0.0
        eligible_investments = 0.0
        total_ifb = 0.0
        total_ifb_uncapped = 0.0

        for inv in self.investments:
            amount = float(inv.get("betrag", 0))
            name = inv.get("bezeichnung", "Unbekannt")
            category = inv.get("kategorie", "standard")

            eligible, rate, reason = self.check_ifb_eligibility(inv)
            ifb_amount = round(amount * rate, 2) if eligible else 0.0

            details.append({
                "bezeichnung": name,
                "betrag": amount,
                "kategorie": category,
                "ifb_faehig": eligible,
                "ifb_satz": f"{rate * 100:.0f} %" if eligible else "—",
                "ifb_betrag": ifb_amount,
                "grund": reason,
            })

            total_investments += amount
            if eligible:
                eligible_investments += amount
                total_ifb_uncapped += ifb_amount

        # Apply EUR 1M cap
        if eligible_investments > IFB_MAX_COST_BASE:
            cap_factor = IFB_MAX_COST_BASE / eligible_investments
            total_ifb = round(total_ifb_uncapped * cap_factor, 2)
            capped = True
        else:
            total_ifb = round(total_ifb_uncapped, 2)
            capped = False

        # Estimate tax saving
        marginal_rate = self.get_marginal_rate(self.profit) if self.profit > 0 else 0.40
        tax_saving = round(total_ifb * marginal_rate, 2)

        # Forschungsprämie
        research_premium = round(self.research_expenses * FORSCHUNGSPRAEMIE_RATE, 2) if self.research_expenses > 0 else 0.0

        # Gewinnfreibetrag
        gfb = self.calculate_gewinnfreibetrag()

        return {
            "investitionen_detail": details,
            "gesamt_investitionen": round(total_investments, 2),
            "ifb_faehige_investitionen": round(eligible_investments, 2),
            "ifb_betrag_gesamt": total_ifb,
            "ifb_betrag_ungedeckelt": round(total_ifb_uncapped, 2),
            "ifb_deckelung": {
                "angewendet": capped,
                "max_bemessungsgrundlage": IFB_MAX_COST_BASE,
            },
            "steuerersparnis_geschaetzt": {
                "betrag": tax_saving,
                "grenzsteuersatz": f"{marginal_rate * 100:.0f} %",
            },
            "forschungspraemie": {
                "aufwendungen": self.research_expenses,
                "praemie_14_prozent": research_premium,
                "hinweis": "Die Forschungsprämie ist steuerfrei und wird als Gutschrift erstattet.",
            },
            "gewinnfreibetrag": gfb,
            "hinweis_ifb_gfb": (
                "IFB und GFB können nicht für dasselbe Wirtschaftsgut "
                "gleichzeitig geltend gemacht werden."
            ),
        }


def format_human_readable(result: Dict[str, Any]) -> str:
    """Format calculation results for human reading."""
    lines = [
        "=" * 60,
        "  INVESTITIONSFREIBETRAG-BERECHNUNG 2026",
        "=" * 60,
        "",
        "  INVESTITIONEN:",
        f"  {'Bezeichnung':<25} {'Betrag':>12} {'IFB':>5} {'IFB-Betrag':>12} {'Status'}",
        "  " + "-" * 70,
    ]

    for inv in result["investitionen_detail"]:
        status = "JA" if inv["ifb_faehig"] else "NEIN"
        lines.append(
            f"  {inv['bezeichnung']:<25} EUR {inv['betrag']:>8,.2f} "
            f"{inv['ifb_satz']:>5} EUR {inv['ifb_betrag']:>8,.2f}  {status} {inv['grund']}"
        )

    lines.extend([
        "",
        f"  Investitionen gesamt:         EUR {result['gesamt_investitionen']:>12,.2f}",
        f"  IFB-fähige Investitionen:     EUR {result['ifb_faehige_investitionen']:>12,.2f}",
        "",
        "-" * 60,
        f"  INVESTITIONSFREIBETRAG:       EUR {result['ifb_betrag_gesamt']:>12,.2f}",
    ])

    if result["ifb_deckelung"]["angewendet"]:
        lines.append(f"  (Gedeckelt — max. Bemessungsgrundlage EUR {result['ifb_deckelung']['max_bemessungsgrundlage']:,.0f})")

    lines.extend([
        f"  Geschätzte Steuerersparnis:   EUR {result['steuerersparnis_geschaetzt']['betrag']:>12,.2f}",
        f"  (bei Grenzsteuersatz {result['steuerersparnis_geschaetzt']['grenzsteuersatz']})",
        "-" * 60,
        "",
    ])

    if result["forschungspraemie"]["aufwendungen"] > 0:
        fp = result["forschungspraemie"]
        lines.extend([
            f"  FORSCHUNGSPRÄMIE (14 %):",
            f"  F&E-Aufwendungen:             EUR {fp['aufwendungen']:>12,.2f}",
            f"  Prämie:                       EUR {fp['praemie_14_prozent']:>12,.2f}",
            f"  {fp['hinweis']}",
            "",
        ])

    gfb = result["gewinnfreibetrag"]
    lines.extend([
        "  GEWINNFREIBETRAG:",
        f"  Gewinn:                       EUR {gfb['gewinn']:>12,.2f}",
        f"  Grundfreibetrag:              EUR {gfb['grundfreibetrag']:>12,.2f}",
        f"  Investitionsbedingter GFB:    EUR {gfb['investitionsbedingter_gfb']:>12,.2f}",
        f"  GFB gesamt:                   EUR {gfb['gesamt_gfb']:>12,.2f}",
        "",
        f"  {result['hinweis_ifb_gfb']}",
        "",
        "  Hinweis: Keine Steuerberatung. Alle Berechnungen sind",
        "  Richtwerte.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Österreichischer Investitionsfreibetrag-Rechner 2026"
    )
    parser.add_argument("input_file", help="JSON-Datei mit Investitionsdaten (oder '-' für stdin)")
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

    if "investitionen" not in data:
        print("Fehler: 'investitionen' ist erforderlich.", file=sys.stderr)
        sys.exit(1)

    calculator = InvestmentAllowanceCalculator(data)
    result = calculator.calculate()

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_human_readable(result))


if __name__ == "__main__":
    main()
