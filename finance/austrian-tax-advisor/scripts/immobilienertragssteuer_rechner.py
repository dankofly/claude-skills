#!/usr/bin/env python3
"""
Austrian Real Estate Capital Gains Tax Calculator 2026

Calculates ImmoESt (30%), handles Alt-/Neuvermögen distinction,
Hauptwohnsitzbefreiung, Herstellerbefreiung, and inflation adjustment.

Usage:
    python immobilienertragssteuer_rechner.py input.json
    python immobilienertragssteuer_rechner.py input.json --format json
"""

import argparse
import json
import sys
from datetime import date, datetime
from typing import Any, Dict, Optional


IMMOEST_RATE = 0.30
ALTVERM_PAUSCHAL_RATE = 0.042  # 4.2% of selling price
ALTVERM_UMWIDMUNG_RATE = 0.18  # 18% of selling price
INFLATION_REDUCTION_PCT = 0.02  # 2% per year from year 11
INFLATION_MAX_REDUCTION = 0.50  # max 50% of gain
STICHTAG_ALTVERMOEGEN = date(2012, 3, 31)


class RealEstateTaxCalculator:
    """Calculate Austrian ImmoESt for 2026."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.purchase_date = self._parse_date(data.get("kaufdatum", "2020-01-01"))
        self.purchase_price = float(data.get("kaufpreis", 0))
        self.sale_date = self._parse_date(data.get("verkaufsdatum", "2026-03-01"))
        self.sale_price = float(data.get("verkaufspreis", 0))
        self.is_primary_residence = bool(data.get("ist_hauptwohnsitz", False))
        self.residence_years = float(data.get("hauptwohnsitz_jahre", 0))
        self.is_self_built = bool(data.get("ist_selbst_hergestellt", False))
        self.construction_costs = float(data.get("herstellungskosten", 0))
        self.renovation_costs = float(data.get("instandsetzungskosten", 0))
        self.purchase_ancillary = float(data.get("nebenkosten_kauf", 0))
        self.sale_ancillary = float(data.get("nebenkosten_verkauf", 0))
        self.rezoning_after_1987 = bool(data.get("umwidmung_nach_1987", False))
        self.was_rented_last_10y = bool(data.get("vermietet_letzte_10_jahre", False))

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """Parse a date string (YYYY-MM-DD)."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return date(2020, 1, 1)

    def classify_asset(self) -> str:
        """Classify as Altvermögen or Neuvermögen."""
        if self.purchase_date <= STICHTAG_ALTVERMOEGEN:
            return "Altvermögen"
        return "Neuvermögen"

    def check_exemptions(self) -> Dict[str, Any]:
        """Check for tax exemptions."""
        exemptions = {
            "hauptwohnsitz_variante_1": False,
            "hauptwohnsitz_variante_2": False,
            "herstellerbefreiung": False,
            "ist_befreit": False,
            "grund": "",
        }

        # Hauptwohnsitzbefreiung Variante 1: 2+ years continuously since purchase
        if self.is_primary_residence and self.residence_years >= 2:
            holding_years = (self.sale_date - self.purchase_date).days / 365.25
            if self.residence_years >= holding_years * 0.9:  # approximately continuous
                exemptions["hauptwohnsitz_variante_1"] = True
                exemptions["ist_befreit"] = True
                exemptions["grund"] = (
                    "Hauptwohnsitzbefreiung (Variante 1): Durchgehend mindestens "
                    "2 Jahre seit Anschaffung als Hauptwohnsitz genutzt."
                )

        # Hauptwohnsitzbefreiung Variante 2: 5+ years in last 10 years
        if self.is_primary_residence and self.residence_years >= 5:
            exemptions["hauptwohnsitz_variante_2"] = True
            exemptions["ist_befreit"] = True
            exemptions["grund"] = (
                "Hauptwohnsitzbefreiung (Variante 2): Mindestens 5 Jahre "
                "durchgehend als Hauptwohnsitz innerhalb der letzten 10 Jahre."
            )

        # Herstellerbefreiung
        if self.is_self_built and not self.was_rented_last_10y:
            exemptions["herstellerbefreiung"] = True
            exemptions["ist_befreit"] = True
            exemptions["grund"] = (
                "Herstellerbefreiung: Selbst hergestelltes Gebäude, "
                "nicht zur Einkünfteerzielung in den letzten 10 Jahren genutzt."
            )

        return exemptions

    def calculate_holding_years(self) -> int:
        """Calculate full holding years."""
        delta = self.sale_date - self.purchase_date
        return int(delta.days / 365.25)

    def calculate_inflation_adjustment(self, gain: float, holding_years: int) -> Dict[str, Any]:
        """Calculate inflation adjustment for Neuvermögen (from year 11)."""
        if holding_years < 11:
            return {
                "haltedauer_jahre": holding_years,
                "bereinigung_prozent": 0.0,
                "bereinigter_gewinn": gain,
                "ersparnis": 0.0,
                "anwendbar": False,
            }

        reduction_years = holding_years - 10
        reduction_pct = min(reduction_years * INFLATION_REDUCTION_PCT, INFLATION_MAX_REDUCTION)
        reduction_amount = round(gain * reduction_pct, 2)
        adjusted_gain = round(gain - reduction_amount, 2)

        return {
            "haltedauer_jahre": holding_years,
            "bereinigung_jahre": reduction_years,
            "bereinigung_prozent": round(reduction_pct * 100, 2),
            "bereinigter_gewinn": max(adjusted_gain, 0),
            "ersparnis": reduction_amount,
            "anwendbar": True,
        }

    def calculate_altverm_alternatives(self) -> Dict[str, Any]:
        """Calculate alternative taxation for Altvermögen."""
        pauschal_4_2 = round(self.sale_price * ALTVERM_PAUSCHAL_RATE, 2)

        if self.rezoning_after_1987:
            pauschal_18 = round(self.sale_price * ALTVERM_UMWIDMUNG_RATE, 2)
        else:
            pauschal_18 = None

        # Actual gain calculation
        total_costs = (
            self.purchase_price
            + self.construction_costs
            + self.renovation_costs
            + self.purchase_ancillary
            + self.sale_ancillary
        )
        actual_gain = max(self.sale_price - total_costs, 0)
        gewinn_30 = round(actual_gain * IMMOEST_RATE, 2)

        # Find cheapest option
        options = [("Pauschal 4,2 %", pauschal_4_2)]
        if pauschal_18 is not None:
            options.append(("Pauschal 18 % (Umwidmung)", pauschal_18))
        options.append(("30 % vom Gewinn", gewinn_30))

        cheapest = min(options, key=lambda x: x[1])

        return {
            "pauschal_4_2_prozent": pauschal_4_2,
            "pauschal_18_prozent": pauschal_18,
            "gewinn_30_prozent": gewinn_30,
            "verauesserungsgewinn": round(actual_gain, 2),
            "guenstigste_variante": cheapest[0],
            "guenstigster_betrag": cheapest[1],
        }

    def calculate(self) -> Dict[str, Any]:
        """Run the full ImmoESt calculation."""
        asset_type = self.classify_asset()
        exemptions = self.check_exemptions()
        holding_years = self.calculate_holding_years()

        # If exempt, no tax
        if exemptions["ist_befreit"]:
            return {
                "kaufdatum": self.purchase_date.isoformat(),
                "kaufpreis": self.purchase_price,
                "verkaufsdatum": self.sale_date.isoformat(),
                "verkaufspreis": self.sale_price,
                "vermoegensart": asset_type,
                "haltedauer_jahre": holding_years,
                "befreiung": exemptions,
                "immoest": 0.0,
                "effektiver_steuersatz": "0,00 %",
            }

        # Calculate costs
        total_acquisition = (
            self.purchase_price
            + self.construction_costs
            + self.renovation_costs
            + self.purchase_ancillary
        )

        gain = max(self.sale_price - total_acquisition - self.sale_ancillary, 0)

        if asset_type == "Altvermögen":
            alternatives = self.calculate_altverm_alternatives()
            immoest = alternatives["guenstigster_betrag"]
            effective_rate = round(immoest / self.sale_price * 100, 2) if self.sale_price > 0 else 0.0

            return {
                "kaufdatum": self.purchase_date.isoformat(),
                "kaufpreis": self.purchase_price,
                "verkaufsdatum": self.sale_date.isoformat(),
                "verkaufspreis": self.sale_price,
                "vermoegensart": asset_type,
                "haltedauer_jahre": holding_years,
                "befreiung": exemptions,
                "berechnung": {
                    "anschaffungskosten_gesamt": round(total_acquisition, 2),
                    "nebenkosten_verkauf": self.sale_ancillary,
                    "verauesserungsgewinn": round(gain, 2),
                },
                "alternativberechnung": alternatives,
                "immoest": immoest,
                "effektiver_steuersatz": f"{effective_rate:.2f} %",
            }
        else:
            # Neuvermögen
            inflation = self.calculate_inflation_adjustment(gain, holding_years)
            taxable_gain = inflation["bereinigter_gewinn"]
            immoest = round(taxable_gain * IMMOEST_RATE, 2)
            effective_rate = round(immoest / self.sale_price * 100, 2) if self.sale_price > 0 else 0.0

            return {
                "kaufdatum": self.purchase_date.isoformat(),
                "kaufpreis": self.purchase_price,
                "verkaufsdatum": self.sale_date.isoformat(),
                "verkaufspreis": self.sale_price,
                "vermoegensart": asset_type,
                "haltedauer_jahre": holding_years,
                "befreiung": exemptions,
                "berechnung": {
                    "anschaffungskosten_gesamt": round(total_acquisition, 2),
                    "herstellungskosten": self.construction_costs,
                    "instandsetzungskosten": self.renovation_costs,
                    "nebenkosten_kauf": self.purchase_ancillary,
                    "nebenkosten_verkauf": self.sale_ancillary,
                    "verauesserungsgewinn": round(gain, 2),
                },
                "inflationsbereinigung": inflation,
                "steuerpflichtiger_gewinn": round(taxable_gain, 2),
                "immoest": immoest,
                "effektiver_steuersatz": f"{effective_rate:.2f} %",
            }


def format_human_readable(result: Dict[str, Any]) -> str:
    """Format calculation results for human reading."""
    lines = [
        "=" * 60,
        "  IMMOBILIENERTRAGSTEUER-BERECHNUNG 2026",
        "=" * 60,
        "",
        f"  Kaufdatum:                    {result['kaufdatum']}",
        f"  Kaufpreis:                    EUR {result['kaufpreis']:>12,.2f}",
        f"  Verkaufsdatum:                {result['verkaufsdatum']}",
        f"  Verkaufspreis:                EUR {result['verkaufspreis']:>12,.2f}",
        f"  Haltedauer:                   {result['haltedauer_jahre']} Jahre",
        f"  Vermögensart:                 {result['vermoegensart']}",
        "",
    ]

    bef = result["befreiung"]
    if bef["ist_befreit"]:
        lines.extend([
            f"  BEFREIUNG: {bef['grund']}",
            "",
            "-" * 60,
            "  IMMOBILIENERTRAGSTEUER:       EUR         0,00",
            "-" * 60,
        ])
    else:
        calc = result.get("berechnung", {})
        lines.extend([
            f"  Anschaffungskosten gesamt:    EUR {calc.get('anschaffungskosten_gesamt', 0):>12,.2f}",
            f"  Nebenkosten Verkauf:          EUR {calc.get('nebenkosten_verkauf', 0):>12,.2f}",
            f"  Veräußerungsgewinn:           EUR {calc.get('verauesserungsgewinn', 0):>12,.2f}",
            "",
        ])

        if result["vermoegensart"] == "Altvermögen":
            alt = result["alternativberechnung"]
            lines.extend([
                "  ALTERNATIVBERECHNUNG (Altvermögen):",
                f"  Pauschal 4,2 %:               EUR {alt['pauschal_4_2_prozent']:>12,.2f}",
            ])
            if alt["pauschal_18_prozent"] is not None:
                lines.append(f"  Pauschal 18 % (Umwidmung):    EUR {alt['pauschal_18_prozent']:>12,.2f}")
            lines.extend([
                f"  30 % vom Gewinn:              EUR {alt['gewinn_30_prozent']:>12,.2f}",
                f"  -> Guenstigste: {alt['guenstigste_variante']}",
                "",
            ])
        else:
            infl = result.get("inflationsbereinigung", {})
            if infl.get("anwendbar"):
                lines.extend([
                    f"  Inflationsbereinigung:        {infl['bereinigung_prozent']:.1f} % ({infl['bereinigung_jahre']} Jahre ab Jahr 11)",
                    f"  Ersparnis:                    EUR {infl['ersparnis']:>12,.2f}",
                    f"  Bereinigter Gewinn:           EUR {infl['bereinigter_gewinn']:>12,.2f}",
                    "",
                ])

        lines.extend([
            "-" * 60,
            f"  IMMOBILIENERTRAGSTEUER:       EUR {result['immoest']:>12,.2f}",
            f"  Effektiver Steuersatz:        {result['effektiver_steuersatz']}",
            "-" * 60,
        ])

    lines.extend([
        "",
        "  Hinweis: Keine Steuerberatung. Alle Berechnungen sind",
        "  Richtwerte. Die ImmoESt wird idR vom Notar einbehalten.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Österreichischer Immobilienertragsteuer-Rechner 2026"
    )
    parser.add_argument("input_file", help="JSON-Datei mit Immobiliendaten (oder '-' für stdin)")
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

    required = ["kaufpreis", "verkaufspreis"]
    missing = [f for f in required if f not in data]
    if missing:
        print(f"Fehler: Fehlende Pflichtfelder: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    calculator = RealEstateTaxCalculator(data)
    result = calculator.calculate()

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_human_readable(result))


if __name__ == "__main__":
    main()
