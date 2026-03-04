#!/usr/bin/env python3
"""
Austrian Income Tax Calculator 2026

Calculates ESt based on the 7-bracket tariff for 2026, applies tax credits
(Absetzbeträge), Familienbonus Plus, and Gewinnfreibetrag.

Usage:
    python einkommensteuer_rechner.py input.json
    python einkommensteuer_rechner.py input.json --format json
    echo '{"bruttoeinkommen": 75000}' | python einkommensteuer_rechner.py -
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ESt tariff brackets 2026 (lower bound, upper bound, marginal rate)
TAX_BRACKETS: List[Tuple[float, float, float]] = [
    (0.00, 13_539.00, 0.00),
    (13_539.01, 21_992.00, 0.20),
    (21_992.01, 36_458.00, 0.30),
    (36_458.01, 70_365.00, 0.40),
    (70_365.01, 104_859.00, 0.48),
    (104_859.01, 1_000_000.00, 0.50),
    (1_000_000.01, float("inf"), 0.55),
]

# Pre-calculated cumulative tax at the start of each bracket
BRACKET_BASE_TAX: List[float] = [
    0.00,
    0.00,
    1_690.60,
    5_830.40,
    19_393.20,
    35_950.32,
    483_520.82,
]


class IncomeTaxCalculator:
    """Calculate Austrian income tax (ESt) for 2026."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.gross_income: float = float(data.get("bruttoeinkommen", 0))
        self.deductions: float = float(data.get("abzuege", 0))
        self.children: int = int(data.get("kinder", 0))
        self.children_over_18: int = int(data.get("kinder_ueber_18", 0))
        self.sole_earner: bool = bool(data.get("alleinverdiener", False))
        self.single_parent: bool = bool(data.get("alleinerzieher", False))
        self.commuter_allowance: float = float(data.get("pendlerpauschale", 0))
        self.special_expenses: float = float(data.get("sonderausgaben", 0))
        self.church_tax: float = float(data.get("kirchenbeitrag", 0))
        self.is_self_employed: bool = bool(data.get("selbstaendig", False))
        self.profit: float = float(data.get("gewinn", 0))

    def calculate_tax(self, taxable_income: float) -> float:
        """Calculate gross income tax using the progressive bracket formula."""
        if taxable_income <= 0:
            return 0.0

        tax = 0.0
        for i, (lower, upper, rate) in enumerate(TAX_BRACKETS):
            if taxable_income <= 0:
                break
            if taxable_income >= lower:
                bracket_income = min(taxable_income, upper) - (lower - 0.01 if i > 0 else 0)
                if i > 0:
                    bracket_income = min(taxable_income, upper) - lower + 0.01
                tax = BRACKET_BASE_TAX[i] + (min(taxable_income, upper) - (lower - 0.01)) * rate
                if taxable_income <= upper:
                    break

        return round(tax, 2)

    def calculate_gewinnfreibetrag(self, profit: float) -> float:
        """Calculate Gewinnfreibetrag (profit allowance) up to 15%, max EUR 46,400."""
        if profit <= 0:
            return 0.0
        if profit <= 33_000:
            return round(profit * 0.15, 2)
        if profit >= 583_000:
            return 46_400.00
        # Linear phase-out between 33,000 and 583,000
        base = 33_000 * 0.15  # 4,950
        remaining = min(profit, 583_000) - 33_000
        max_remaining = 583_000 - 33_000
        additional = (46_400 - base) * (remaining / max_remaining)
        return round(base + additional, 2)

    def get_marginal_rate(self, taxable_income: float) -> float:
        """Return the marginal tax rate for a given taxable income."""
        for lower, upper, rate in TAX_BRACKETS:
            if taxable_income <= upper:
                return rate
        return 0.55

    def calculate_verkehrsabsetzbetrag(self, income: float) -> float:
        """Calculate Verkehrsabsetzbetrag (commuter tax credit)."""
        if income <= 16_832:
            return 798.00
        if income <= 28_967:
            # Phase-out from 798 to 463
            reduction = (income - 16_832) / (28_967 - 16_832) * (798 - 463)
            return round(798.00 - reduction, 2)
        return 463.00

    def calculate_avab_aeab(self) -> float:
        """Calculate Alleinverdiener-/Alleinerzieherabsetzbetrag."""
        if not self.sole_earner and not self.single_parent:
            return 0.0
        total_children = self.children + self.children_over_18
        if total_children == 0:
            return 0.0
        if total_children == 1:
            return 572.00
        if total_children == 2:
            return 774.00
        return 774.00 + (total_children - 2) * 255.00

    def calculate_familienbonus(self) -> Tuple[float, List[Dict[str, Any]]]:
        """Calculate Familienbonus Plus."""
        details = []
        total = 0.0
        for i in range(self.children):
            bonus = 2_000.00
            details.append({"kind": i + 1, "alter": "unter 18", "bonus": bonus})
            total += bonus
        for i in range(self.children_over_18):
            bonus = 700.00
            details.append({"kind": self.children + i + 1, "alter": "über 18", "bonus": bonus})
            total += bonus
        return total, details

    def calculate(self) -> Dict[str, Any]:
        """Run the full income tax calculation."""
        # Determine income base
        if self.is_self_employed and self.profit > 0:
            base_income = self.profit
            gfb = self.calculate_gewinnfreibetrag(self.profit)
        else:
            base_income = self.gross_income
            gfb = 0.0

        # Deductions
        church_deduction = min(self.church_tax, 600.00)
        total_deductions = (
            self.deductions
            + self.commuter_allowance
            + self.special_expenses
            + church_deduction
            + gfb
        )

        taxable_income = max(base_income - total_deductions, 0)

        # Gross tax
        gross_tax = self.calculate_tax(taxable_income)
        marginal_rate = self.get_marginal_rate(taxable_income)

        # Tax credits (Absetzbeträge)
        credits: List[Dict[str, Any]] = []

        # Verkehrsabsetzbetrag (only for employees)
        if not self.is_self_employed:
            vab = self.calculate_verkehrsabsetzbetrag(taxable_income)
            credits.append({"name": "Verkehrsabsetzbetrag", "betrag": vab})

        # AVAB / AEAB
        avab = self.calculate_avab_aeab()
        if avab > 0:
            label = "Alleinerzieherabsetzbetrag" if self.single_parent else "Alleinverdienerabsetzbetrag"
            credits.append({"name": label, "betrag": avab})

        # Familienbonus Plus
        familienbonus_total, familienbonus_details = self.calculate_familienbonus()
        if familienbonus_total > 0:
            credits.append({"name": "Familienbonus Plus", "betrag": familienbonus_total})

        total_credits = sum(c["betrag"] for c in credits)
        net_tax = max(gross_tax - total_credits, 0)

        # Kindermehrbetrag for AVAB/AEAB with low tax
        kindermehrbetrag = 0.0
        if (self.sole_earner or self.single_parent) and gross_tax < total_credits:
            kindermehrbetrag = min(700.00, total_credits - gross_tax)

        effective_rate = round(net_tax / base_income * 100, 2) if base_income > 0 else 0.0

        return {
            "bruttoeinkommen": base_income,
            "abzuege": {
                "werbungskosten_betriebsausgaben": self.deductions,
                "pendlerpauschale": self.commuter_allowance,
                "sonderausgaben": self.special_expenses,
                "kirchenbeitrag": church_deduction,
                "gewinnfreibetrag": gfb,
                "gesamt": round(total_deductions, 2),
            },
            "zu_versteuerndes_einkommen": round(taxable_income, 2),
            "einkommensteuer_brutto": gross_tax,
            "absetzbetraege": credits,
            "absetzbetraege_gesamt": round(total_credits, 2),
            "familienbonus_plus": {
                "gesamt": familienbonus_total,
                "details": familienbonus_details,
            },
            "kindermehrbetrag": kindermehrbetrag,
            "einkommensteuer_netto": round(net_tax, 2),
            "grenzsteuersatz": f"{marginal_rate * 100:.0f} %",
            "effektivsteuersatz": f"{effective_rate:.2f} %",
        }


def format_human_readable(result: Dict[str, Any]) -> str:
    """Format calculation results for human reading."""
    lines = [
        "=" * 60,
        "  EINKOMMENSTEUER-BERECHNUNG 2026",
        "=" * 60,
        "",
        f"  Bruttoeinkommen:              EUR {result['bruttoeinkommen']:>12,.2f}",
        f"  Abzüge gesamt:                EUR {result['abzuege']['gesamt']:>12,.2f}",
    ]

    if result["abzuege"]["werbungskosten_betriebsausgaben"] > 0:
        lines.append(f"    Werbungskosten/BA:          EUR {result['abzuege']['werbungskosten_betriebsausgaben']:>12,.2f}")
    if result["abzuege"]["pendlerpauschale"] > 0:
        lines.append(f"    Pendlerpauschale:           EUR {result['abzuege']['pendlerpauschale']:>12,.2f}")
    if result["abzuege"]["sonderausgaben"] > 0:
        lines.append(f"    Sonderausgaben:             EUR {result['abzuege']['sonderausgaben']:>12,.2f}")
    if result["abzuege"]["kirchenbeitrag"] > 0:
        lines.append(f"    Kirchenbeitrag:             EUR {result['abzuege']['kirchenbeitrag']:>12,.2f}")
    if result["abzuege"]["gewinnfreibetrag"] > 0:
        lines.append(f"    Gewinnfreibetrag:           EUR {result['abzuege']['gewinnfreibetrag']:>12,.2f}")

    lines.extend([
        "",
        f"  Zu versteuerndes Einkommen:   EUR {result['zu_versteuerndes_einkommen']:>12,.2f}",
        f"  Einkommensteuer (brutto):     EUR {result['einkommensteuer_brutto']:>12,.2f}",
        "",
        "  Absetzbeträge:",
    ])

    for credit in result["absetzbetraege"]:
        lines.append(f"    {credit['name']:<30} EUR {credit['betrag']:>10,.2f}")

    lines.extend([
        f"  Absetzbeträge gesamt:         EUR {result['absetzbetraege_gesamt']:>12,.2f}",
        "",
    ])

    if result["familienbonus_plus"]["gesamt"] > 0:
        lines.append(f"  Familienbonus Plus:           EUR {result['familienbonus_plus']['gesamt']:>12,.2f}")
        for d in result["familienbonus_plus"]["details"]:
            lines.append(f"    Kind {d['kind']} ({d['alter']}):          EUR {d['bonus']:>10,.2f}")
        lines.append("")

    if result["kindermehrbetrag"] > 0:
        lines.append(f"  Kindermehrbetrag:             EUR {result['kindermehrbetrag']:>12,.2f}")
        lines.append("")

    lines.extend([
        "-" * 60,
        f"  EINKOMMENSTEUER (netto):      EUR {result['einkommensteuer_netto']:>12,.2f}",
        "-" * 60,
        "",
        f"  Grenzsteuersatz:              {result['grenzsteuersatz']}",
        f"  Effektivsteuersatz:           {result['effektivsteuersatz']}",
        "",
        "  Hinweis: Keine Steuerberatung. Alle Berechnungen sind",
        "  Richtwerte. Für verbindliche Auskünfte wenden Sie sich",
        "  an einen Steuerberater.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Österreichischer Einkommensteuer-Rechner 2026"
    )
    parser.add_argument(
        "input_file",
        help="JSON-Datei mit Steuerdaten (oder '-' für stdin)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Ausgabeformat (default: text)",
    )
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

    if "bruttoeinkommen" not in data and "gewinn" not in data:
        print("Fehler: 'bruttoeinkommen' oder 'gewinn' ist erforderlich.", file=sys.stderr)
        sys.exit(1)

    calculator = IncomeTaxCalculator(data)
    result = calculator.calculate()

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_human_readable(result))


if __name__ == "__main__":
    main()
