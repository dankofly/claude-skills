#!/usr/bin/env python3
"""
Austrian VAT Calculator 2026

Calculates USt liability, checks Kleinunternehmerregelung (EUR 55,000),
and provides recommendations on opting for standard taxation.

Usage:
    python umsatzsteuer_rechner.py input.json
    python umsatzsteuer_rechner.py input.json --format json
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


KLEINUNTERNEHMER_GRENZE = 55_000.00
KLEINUNTERNEHMER_TOLERANZ = 60_500.00  # 10% overshoot once per 5 years

UST_RATES = {
    20: "Normalsteuersatz",
    13: "Ermäßigt (Beherbergung, Kultur, Tiere)",
    10: "Ermäßigt (Lebensmittel, Bücher, Medikamente, Wohnraumvermietung)",
    0: "Steuerbefreit (Export, ig Lieferung)",
}


class VATCalculator:
    """Calculate Austrian VAT (USt) for 2026."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.revenues: List[Dict[str, Any]] = data.get("umsaetze", [])
        self.input_vat: float = float(data.get("vorsteuer", 0))
        self.is_small_business: Optional[bool] = data.get("ist_kleinunternehmer")

    def calculate(self) -> Dict[str, Any]:
        """Run the full VAT calculation."""
        # Calculate per-item details
        details = []
        total_net = 0.0
        total_vat = 0.0
        total_gross = 0.0
        vat_by_rate: Dict[int, float] = {}

        for item in self.revenues:
            net = float(item.get("netto", 0))
            rate = int(item.get("steuersatz", 20))
            vat_amount = round(net * rate / 100, 2)
            gross = round(net + vat_amount, 2)

            details.append({
                "bezeichnung": item.get("bezeichnung", "Unbekannt"),
                "netto": net,
                "steuersatz": rate,
                "steuersatz_bezeichnung": UST_RATES.get(rate, f"{rate} %"),
                "ust_betrag": vat_amount,
                "brutto": gross,
            })

            total_net += net
            total_vat += vat_amount
            total_gross += gross
            vat_by_rate[rate] = vat_by_rate.get(rate, 0) + vat_amount

        total_net = round(total_net, 2)
        total_vat = round(total_vat, 2)
        total_gross = round(total_gross, 2)

        # Determine Kleinunternehmer status
        if self.is_small_business is None:
            is_ku = total_gross < KLEINUNTERNEHMER_GRENZE
        else:
            is_ku = self.is_small_business

        ku_status = {
            "ist_kleinunternehmer": is_ku,
            "umsatz_brutto": total_gross,
            "grenze": KLEINUNTERNEHMER_GRENZE,
            "toleranz_grenze": KLEINUNTERNEHMER_TOLERANZ,
            "ueberschreitung": max(total_gross - KLEINUNTERNEHMER_GRENZE, 0),
            "innerhalb_toleranz": total_gross <= KLEINUNTERNEHMER_TOLERANZ,
        }

        # Calculate liability
        if is_ku:
            zahllast = 0.0
            vorsteuer_abzug = 0.0
            ersparnis_ku = total_vat  # USt that doesn't need to be charged
        else:
            zahllast = round(total_vat - self.input_vat, 2)
            vorsteuer_abzug = self.input_vat
            ersparnis_ku = 0.0

        # Recommendation
        empfehlung = self._generate_recommendation(
            is_ku, total_gross, self.input_vat, total_vat
        )

        # VAT breakdown by rate
        aufschluesselung = [
            {"steuersatz": rate, "bezeichnung": UST_RATES.get(rate, ""), "ust_betrag": round(amount, 2)}
            for rate, amount in sorted(vat_by_rate.items(), reverse=True)
        ]

        # UVA period determination
        if total_net > 100_000:
            uva_zeitraum = "Monatlich"
        elif total_net > 35_000:
            uva_zeitraum = "Vierteljährlich"
        else:
            uva_zeitraum = "Keine UVA-Pflicht (nur Jahreserklärung)"

        return {
            "umsaetze_detail": details,
            "gesamt_netto": total_net,
            "gesamt_ust": total_vat,
            "gesamt_brutto": total_gross,
            "aufschluesselung_nach_steuersatz": aufschluesselung,
            "vorsteuer": self.input_vat,
            "vorsteuer_abzug": vorsteuer_abzug,
            "zahllast": zahllast,
            "kleinunternehmer_status": ku_status,
            "uva_zeitraum": uva_zeitraum,
            "empfehlung": empfehlung,
        }

    def _generate_recommendation(
        self, is_ku: bool, gross: float, input_vat: float, output_vat: float
    ) -> str:
        """Generate a recommendation text."""
        if is_ku:
            if input_vat > output_vat * 0.5:
                return (
                    "Option zur Regelbesteuerung prüfen: Ihre Vorsteuern "
                    f"(EUR {input_vat:,.2f}) sind hoch im Verhältnis zur USt. "
                    "Ein Verzicht auf die Kleinunternehmerbefreiung könnte "
                    "vorteilhaft sein (Bindungsfrist: 5 Jahre)."
                )
            if gross > KLEINUNTERNEHMER_GRENZE * 0.9:
                return (
                    f"Achtung: Ihr Umsatz (EUR {gross:,.2f}) nähert sich der "
                    f"Kleinunternehmergrenze (EUR {KLEINUNTERNEHMER_GRENZE:,.2f}). "
                    "Planen Sie Ihre Umsätze sorgfältig."
                )
            return (
                "Kleinunternehmerregelung ist anwendbar. Kein USt-Abführung "
                "erforderlich, aber auch kein Vorsteuerabzug möglich."
            )
        else:
            return (
                f"USt-Zahllast: EUR {round(output_vat - input_vat, 2):,.2f}. "
                "Achten Sie auf fristgerechte UVA-Abgabe und Zahlung."
            )


def format_human_readable(result: Dict[str, Any]) -> str:
    """Format calculation results for human reading."""
    lines = [
        "=" * 60,
        "  UMSATZSTEUER-BERECHNUNG 2026",
        "=" * 60,
        "",
        "  UMSÄTZE:",
        f"  {'Bezeichnung':<30} {'Netto':>10} {'USt%':>5} {'USt':>10} {'Brutto':>10}",
        "  " + "-" * 65,
    ]

    for item in result["umsaetze_detail"]:
        lines.append(
            f"  {item['bezeichnung']:<30} {item['netto']:>10,.2f} {item['steuersatz']:>4}% "
            f"{item['ust_betrag']:>10,.2f} {item['brutto']:>10,.2f}"
        )

    lines.extend([
        "  " + "-" * 65,
        f"  {'GESAMT':<30} {result['gesamt_netto']:>10,.2f}       "
        f"{result['gesamt_ust']:>10,.2f} {result['gesamt_brutto']:>10,.2f}",
        "",
    ])

    ku = result["kleinunternehmer_status"]
    status = "JA" if ku["ist_kleinunternehmer"] else "NEIN"
    lines.extend([
        f"  Kleinunternehmer:             {status}",
        f"  Bruttoumsatz:                 EUR {ku['umsatz_brutto']:>12,.2f}",
        f"  Grenze:                       EUR {ku['grenze']:>12,.2f}",
        "",
    ])

    if not ku["ist_kleinunternehmer"]:
        lines.extend([
            f"  USt (geschuldet):             EUR {result['gesamt_ust']:>12,.2f}",
            f"  Vorsteuer:                    EUR {result['vorsteuer']:>12,.2f}",
            "-" * 60,
            f"  UST-ZAHLLAST:                 EUR {result['zahllast']:>12,.2f}",
            "-" * 60,
        ])
    else:
        lines.extend([
            "  USt-Zahllast:                 EUR         0,00",
            "  (Kein Vorsteuerabzug als Kleinunternehmer)",
        ])

    lines.extend([
        "",
        f"  UVA-Zeitraum:                 {result['uva_zeitraum']}",
        "",
        f"  Empfehlung: {result['empfehlung']}",
        "",
        "  Hinweis: Keine Steuerberatung. Alle Berechnungen sind",
        "  Richtwerte.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Österreichischer Umsatzsteuer-Rechner 2026"
    )
    parser.add_argument("input_file", help="JSON-Datei mit Umsatzdaten (oder '-' für stdin)")
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

    if "umsaetze" not in data:
        print("Fehler: 'umsaetze' ist erforderlich.", file=sys.stderr)
        sys.exit(1)

    calculator = VATCalculator(data)
    result = calculator.calculate()

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_human_readable(result))


if __name__ == "__main__":
    main()
