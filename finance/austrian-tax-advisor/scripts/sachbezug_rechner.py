#!/usr/bin/env python3
"""
Austrian Fringe Benefits Calculator 2026

Calculates Sachbezugswerte for company cars (CO2-based),
tax-free employee benefits, and employer cost savings.

Usage:
    python sachbezug_rechner.py input.json
    python sachbezug_rechner.py input.json --format json
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


# PKW Sachbezug thresholds
CO2_GRENZWERT_2026 = 129  # g/km WLTP
SACHBEZUG_STANDARD_PCT = 0.02
SACHBEZUG_NIEDRIG_PCT = 0.015
SACHBEZUG_STANDARD_CAP = 960.00
SACHBEZUG_NIEDRIG_CAP = 720.00

# Tax-free benefit limits
BENEFIT_LIMITS = {
    "zukunftssicherung": {"limit": 300.00, "period": "Jahr", "label": "Zukunftssicherung (§ 3 Abs. 1 Z 15a)"},
    "mitarbeiterrabatt": {"limit": 1_000.00, "period": "Jahr", "label": "Mitarbeiterrabatt"},
    "essensgutscheine_gaststaette": {"per_day": 8.00, "label": "Essensgutscheine (Gaststätte)"},
    "essensgutscheine_lebensmittel": {"per_day": 2.00, "label": "Essensgutscheine (Lebensmittel)"},
    "oeffi_ticket": {"limit": float("inf"), "period": "Jahr", "label": "Öffi-Ticket / Klimaticket"},
    "kinderbetreuung": {"limit": 2_000.00, "period": "Jahr", "label": "Kinderbetreuungszuschuss (pro Kind)"},
    "gewinnbeteiligung": {"limit": 3_000.00, "period": "Jahr", "label": "Mitarbeitergewinnbeteiligung"},
    "startup_beteiligung": {"limit": 4_500.00, "period": "Jahr", "label": "Startup-Mitarbeiterbeteiligung"},
    "betriebsveranstaltung": {"limit": 365.00, "period": "Jahr", "label": "Betriebsveranstaltungen"},
    "weihnachtsgeschenk": {"limit": 186.00, "period": "Jahr", "label": "Weihnachtsgeschenk"},
    "e_bike": {"limit": float("inf"), "period": "Jahr", "label": "Dienst-E-Bike / E-Scooter"},
    "carsharing": {"limit": 200.00, "period": "Jahr", "label": "Carsharing-Zuschuss (CO2-frei)"},
    "wallbox": {"limit": 2_000.00, "period": "einmalig", "label": "Wallbox-Zuschuss"},
    "laden_arbeitgeber": {"limit": float("inf"), "period": "Jahr", "label": "E-Auto Laden beim AG"},
    "laden_zuhause": {"limit": 360.00, "period": "Jahr", "label": "E-Auto Laden zu Hause (EUR 30/Monat)"},
}

ESTIMATED_MARGINAL_RATE = 0.40  # rough estimate for tax impact


class FringeBenefitCalculator:
    """Calculate Austrian fringe benefits (Sachbezüge) for 2026."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.company_car: Optional[Dict[str, Any]] = data.get("dienstwagen")
        self.benefits: List[Dict[str, Any]] = data.get("benefits", [])

    def calculate_car_benefit(self) -> Optional[Dict[str, Any]]:
        """Calculate company car fringe benefit."""
        if not self.company_car:
            return None

        list_price = float(self.company_car.get("listenpreis", 0))
        co2 = int(self.company_car.get("co2_emission", 0))
        is_electric = bool(self.company_car.get("ist_elektro", False))
        private_km = int(self.company_car.get("privat_km_monat", 501))
        half_benefit = private_km <= 500

        if is_electric or co2 == 0:
            pct = 0.0
            cap = 0.0
            category = "Emissionsfrei (E-Auto)"
        elif co2 <= CO2_GRENZWERT_2026:
            pct = SACHBEZUG_NIEDRIG_PCT
            cap = SACHBEZUG_NIEDRIG_CAP
            category = f"Niedrig (bis {CO2_GRENZWERT_2026} g/km)"
        else:
            pct = SACHBEZUG_STANDARD_PCT
            cap = SACHBEZUG_STANDARD_CAP
            category = f"Standard (> {CO2_GRENZWERT_2026} g/km)"

        monthly_raw = round(list_price * pct, 2)
        capped = cap > 0 and monthly_raw > cap
        monthly = min(monthly_raw, cap) if cap > 0 else monthly_raw

        if half_benefit and monthly > 0:
            monthly = round(monthly / 2, 2)
            cap = round(cap / 2, 2)

        yearly = round(monthly * 12, 2)

        return {
            "listenpreis": list_price,
            "co2_emission": co2,
            "ist_elektro": is_electric,
            "kategorie": category,
            "sachbezug_prozent": pct * 100,
            "sachbezug_monatlich_berechnet": monthly_raw,
            "deckelung_monatlich": cap,
            "deckelung_angewendet": capped,
            "halber_sachbezug": half_benefit,
            "sachbezug_monatlich": monthly,
            "sachbezug_jaehrlich": yearly,
        }

    def calculate_benefit(self, benefit: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate a single employee benefit."""
        typ = benefit.get("typ", "unbekannt")
        amount = float(benefit.get("betrag", 0))
        days = int(benefit.get("tage", 0))
        children = int(benefit.get("kinder", 1))

        config = BENEFIT_LIMITS.get(typ)
        if not config:
            return {
                "typ": typ,
                "label": typ,
                "betrag_gesamt": amount,
                "steuerfrei": 0.0,
                "steuerpflichtig": amount,
                "hinweis": "Unbekannter Benefit-Typ",
            }

        label = config["label"]

        # Per-day benefits (Essensgutscheine)
        if "per_day" in config:
            per_day_limit = config["per_day"]
            tax_free = round(min(amount, days * per_day_limit), 2) if days > 0 else 0.0
            total = amount if amount > 0 else round(days * per_day_limit, 2)
            if amount == 0:
                tax_free = total
                total = total
        else:
            total = amount
            limit = config.get("limit", float("inf"))
            if typ == "kinderbetreuung":
                limit = limit * children
            tax_free = round(min(total, limit), 2)

        taxable = round(max(total - tax_free, 0), 2)

        return {
            "typ": typ,
            "label": label,
            "betrag_gesamt": total,
            "steuerfrei": tax_free,
            "steuerpflichtig": taxable,
        }

    def calculate(self) -> Dict[str, Any]:
        """Run the full fringe benefit calculation."""
        car_result = self.calculate_car_benefit()

        benefit_details = []
        total_tax_free = 0.0
        total_taxable = 0.0

        for b in self.benefits:
            detail = self.calculate_benefit(b)
            benefit_details.append(detail)
            total_tax_free += detail["steuerfrei"]
            total_taxable += detail["steuerpflichtig"]

        # Add car benefit to taxable total
        car_taxable = car_result["sachbezug_jaehrlich"] if car_result else 0.0
        total_taxable += car_taxable

        # Estimated tax impact
        estimated_tax_dn = round(total_taxable * ESTIMATED_MARGINAL_RATE, 2)
        estimated_sv_saving_ag = round(total_tax_free * 0.2198, 2)  # approx DG SV rate

        return {
            "dienstwagen_sachbezug": car_result,
            "benefits_detail": benefit_details,
            "gesamt_steuerfrei": round(total_tax_free, 2),
            "gesamt_steuerpflichtig": round(total_taxable, 2),
            "geschaetzte_steuerbelastung_dn": estimated_tax_dn,
            "geschaetzte_sv_ersparnis_ag": estimated_sv_saving_ag,
            "hinweis": (
                f"Geschätzte Werte basieren auf einem angenommenen "
                f"Grenzsteuersatz von {ESTIMATED_MARGINAL_RATE * 100:.0f} %. "
                f"Tatsächliche Belastung hängt vom individuellen Einkommen ab."
            ),
        }


def format_human_readable(result: Dict[str, Any]) -> str:
    """Format calculation results for human reading."""
    lines = [
        "=" * 60,
        "  SACHBEZUGS-BERECHNUNG 2026",
        "=" * 60,
        "",
    ]

    car = result["dienstwagen_sachbezug"]
    if car:
        lines.extend([
            "  DIENSTWAGEN:",
            f"  Listenpreis:                  EUR {car['listenpreis']:>12,.2f}",
            f"  CO2-Emission:                 {car['co2_emission']} g/km",
            f"  Kategorie:                    {car['kategorie']}",
            f"  Sachbezug:                    {car['sachbezug_prozent']:.1f} %",
            f"  Monatlich:                    EUR {car['sachbezug_monatlich']:>12,.2f}",
            f"  Jährlich:                     EUR {car['sachbezug_jaehrlich']:>12,.2f}",
        ])
        if car["deckelung_angewendet"]:
            lines.append(f"  (Deckelung bei EUR {car['deckelung_monatlich']:,.2f}/Monat angewendet)")
        if car["halber_sachbezug"]:
            lines.append("  (Halber Sachbezug — max. 500 km privat/Monat)")
        lines.append("")

    if result["benefits_detail"]:
        lines.extend([
            "  MITARBEITER-BENEFITS:",
            f"  {'Benefit':<35} {'Gesamt':>10} {'Steuerfrei':>12} {'Pflichtig':>10}",
            "  " + "-" * 67,
        ])
        for b in result["benefits_detail"]:
            lines.append(
                f"  {b['label']:<35} {b['betrag_gesamt']:>10,.2f} "
                f"{b['steuerfrei']:>12,.2f} {b['steuerpflichtig']:>10,.2f}"
            )
        lines.append("")

    lines.extend([
        "-" * 60,
        f"  Steuerfrei gesamt:            EUR {result['gesamt_steuerfrei']:>12,.2f}",
        f"  Steuerpflichtig gesamt:       EUR {result['gesamt_steuerpflichtig']:>12,.2f}",
        "",
        f"  Geschätzte Steuer (DN):       EUR {result['geschaetzte_steuerbelastung_dn']:>12,.2f}",
        f"  Geschätzte SV-Ersparnis (AG): EUR {result['geschaetzte_sv_ersparnis_ag']:>12,.2f}",
        "-" * 60,
        "",
        f"  {result['hinweis']}",
        "",
        "  Hinweis: Keine Steuerberatung. Alle Berechnungen sind",
        "  Richtwerte.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Österreichischer Sachbezugs-Rechner 2026"
    )
    parser.add_argument("input_file", help="JSON-Datei mit Sachbezugsdaten (oder '-' für stdin)")
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

    calculator = FringeBenefitCalculator(data)
    result = calculator.calculate()

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_human_readable(result))


if __name__ == "__main__":
    main()
