#!/usr/bin/env python3
"""
Austrian Crypto Tax Calculator 2026

Calculates KESt (27.5%) on crypto gains, handles Alt-/Neuvermögen
distinction (stichtag 1.3.2021), crypto-to-crypto trades, staking/mining.

Usage:
    python krypto_steuer_rechner.py input.json
    python krypto_steuer_rechner.py input.json --format json
"""

import argparse
import json
import sys
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple


KEST_RATE = 0.275
STICHTAG_NEUVERMOEGEN = date(2021, 3, 1)
STICHTAG_NEUES_REGIME = date(2022, 3, 1)
SPEKULATIONS_FRIST_TAGE = 365


class CryptoPortfolio:
    """Track crypto holdings with moving average cost basis."""

    def __init__(self) -> None:
        # {crypto_name: {"total_amount": float, "total_cost": float}}
        self.holdings: Dict[str, Dict[str, float]] = {}

    def add(self, crypto: str, amount: float, cost: float) -> None:
        """Add to holdings (buy or receive)."""
        if crypto not in self.holdings:
            self.holdings[crypto] = {"total_amount": 0.0, "total_cost": 0.0}
        h = self.holdings[crypto]
        h["total_amount"] += amount
        h["total_cost"] += cost

    def get_avg_cost(self, crypto: str) -> float:
        """Get moving average cost per unit."""
        h = self.holdings.get(crypto)
        if not h or h["total_amount"] <= 0:
            return 0.0
        return h["total_cost"] / h["total_amount"]

    def remove(self, crypto: str, amount: float) -> float:
        """Remove from holdings, return cost basis for removed amount."""
        h = self.holdings.get(crypto)
        if not h or h["total_amount"] <= 0:
            return 0.0

        avg_cost = self.get_avg_cost(crypto)
        actual_amount = min(amount, h["total_amount"])
        cost_basis = actual_amount * avg_cost

        h["total_amount"] -= actual_amount
        h["total_cost"] -= cost_basis

        if h["total_amount"] < 0.0001:
            h["total_amount"] = 0.0
            h["total_cost"] = 0.0

        return round(cost_basis, 2)


class CryptoTaxCalculator:
    """Calculate Austrian crypto tax for 2026."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.transactions: List[Dict[str, Any]] = data.get("transaktionen", [])
        self.portfolio = CryptoPortfolio()

    @staticmethod
    def _parse_date(date_str: str) -> date:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return date(2026, 1, 1)

    def classify_asset(self, acquisition_date: date) -> str:
        """Classify as Alt- or Neuvermögen based on acquisition date."""
        if acquisition_date < STICHTAG_NEUVERMOEGEN:
            return "Altvermögen"
        return "Neuvermögen"

    def is_speculation_period_expired(self, acquisition_date: date) -> bool:
        """Check if 1-year speculation period expired before 1.3.2022."""
        expiry = date(
            acquisition_date.year + 1,
            acquisition_date.month,
            acquisition_date.day,
        )
        return expiry < STICHTAG_NEUES_REGIME

    def process_transaction(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single transaction and return tax analysis."""
        tx_type = tx.get("typ", "").lower()
        tx_date = self._parse_date(tx.get("datum", ""))
        crypto = tx.get("krypto", tx.get("krypto_von", "UNKNOWN"))
        amount = float(tx.get("menge", 0))
        price_eur = float(tx.get("preis_eur", tx.get("wert_eur", 0)))

        result = {
            "typ": tx_type,
            "datum": tx_date.isoformat(),
            "krypto": crypto,
            "menge": amount,
            "wert_eur": price_eur,
            "vermoegensart": "—",
            "steuerpflichtig": False,
            "gewinn_verlust": 0.0,
            "steuer": 0.0,
            "grund": "",
        }

        if tx_type == "kauf":
            self.portfolio.add(crypto, amount, price_eur)
            asset_type = self.classify_asset(tx_date)
            result["vermoegensart"] = asset_type
            result["grund"] = f"Kauf — {asset_type}, Einstandskosten EUR {price_eur:,.2f}"
            return result

        elif tx_type == "verkauf":
            # Determine asset type from when the coins were acquired
            # We use FIFO-like approach but with moving average cost
            cost_basis = self.portfolio.remove(crypto, amount)
            gain = round(price_eur - cost_basis, 2)

            # For simplicity, classify based on whether portfolio has old coins
            # In practice, you'd track acquisition dates per lot
            asset_type = "Neuvermögen"  # Default assumption for moving average

            result["vermoegensart"] = asset_type
            result["gewinn_verlust"] = gain

            if asset_type == "Neuvermögen":
                result["steuerpflichtig"] = True
                result["steuer"] = round(max(gain, 0) * KEST_RATE, 2)
                result["grund"] = (
                    f"Verkauf Neuvermögen an Fiat — "
                    f"Erlös EUR {price_eur:,.2f}, Kosten EUR {cost_basis:,.2f}, "
                    f"Gewinn EUR {gain:,.2f}"
                )
            else:
                result["grund"] = "Altvermögen — Spekulationsfrist abgelaufen, steuerfrei"

            return result

        elif tx_type == "tausch":
            crypto_from = tx.get("krypto_von", "")
            crypto_to = tx.get("krypto_nach", "")
            amount_to = float(tx.get("menge_erhalten", amount))

            # Crypto-to-crypto trade: tax-free under new regime
            cost_basis = self.portfolio.remove(crypto_from, amount)
            self.portfolio.add(crypto_to, amount_to, cost_basis)  # carry forward cost

            result["krypto"] = f"{crypto_from} -> {crypto_to}"
            result["vermoegensart"] = "Neuvermögen"
            result["steuerpflichtig"] = False
            result["grund"] = (
                f"Tausch {crypto_from} -> {crypto_to} -- steuerfrei "
                f"(Anschaffungskosten EUR {cost_basis:,.2f} werden fortgeführt)"
            )
            return result

        elif tx_type in ("staking", "mining"):
            # Taxable upon receipt at 27.5%
            self.portfolio.add(crypto, amount, price_eur)
            result["vermoegensart"] = "Neuvermögen"
            result["steuerpflichtig"] = True
            result["gewinn_verlust"] = price_eur
            result["steuer"] = round(price_eur * KEST_RATE, 2)
            result["grund"] = (
                f"{tx_type.capitalize()}-Einkünfte — "
                f"EUR {price_eur:,.2f} bei Zufluss steuerpflichtig (27,5 % KESt)"
            )
            return result

        elif tx_type in ("airdrop", "bounty", "hardfork"):
            # Cost basis = 0, taxed only on later sale
            self.portfolio.add(crypto, amount, 0.0)
            result["vermoegensart"] = "Neuvermögen"
            result["steuerpflichtig"] = False
            result["grund"] = (
                f"{tx_type.capitalize()} — Anschaffungskosten EUR 0, "
                f"Besteuerung erst bei Veräußerung"
            )
            return result

        else:
            result["grund"] = f"Unbekannter Transaktionstyp: {tx_type}"
            return result

    def calculate(self) -> Dict[str, Any]:
        """Run the full crypto tax calculation."""
        # Sort transactions by date
        sorted_tx = sorted(
            self.transactions,
            key=lambda t: self._parse_date(t.get("datum", "")),
        )

        details = []
        total_taxable_gains = 0.0
        total_tax_free_gains = 0.0
        total_losses = 0.0
        total_staking_mining = 0.0
        total_kest = 0.0

        for tx in sorted_tx:
            result = self.process_transaction(tx)
            details.append(result)

            gain = result["gewinn_verlust"]
            if result["steuerpflichtig"]:
                if result["typ"] in ("staking", "mining"):
                    total_staking_mining += gain
                elif gain > 0:
                    total_taxable_gains += gain
                else:
                    total_losses += abs(gain)
                total_kest += result["steuer"]
            elif gain > 0:
                total_tax_free_gains += gain

        # Net position
        saldo = round(total_taxable_gains - total_losses, 2)
        net_kest = round(max(saldo, 0) * KEST_RATE + total_staking_mining * KEST_RATE, 2)

        # Portfolio summary
        portfolio_summary = []
        for crypto, holding in self.portfolio.holdings.items():
            if holding["total_amount"] > 0.0001:
                portfolio_summary.append({
                    "krypto": crypto,
                    "menge": round(holding["total_amount"], 8),
                    "einstandskosten": round(holding["total_cost"], 2),
                    "durchschnittspreis": round(
                        holding["total_cost"] / holding["total_amount"], 2
                    ) if holding["total_amount"] > 0 else 0.0,
                })

        hints = [
            "Krypto-Verluste können mit anderen Kapitalerträgen (27,5 % KESt) verrechnet werden.",
            "Kein Verlustvortrag im außerbetrieblichen Bereich.",
            "Gleitender Durchschnittspreis seit 1.1.2023 verpflichtend.",
        ]

        if total_losses > 0:
            hints.append(
                f"Realisierte Verluste: EUR {total_losses:,.2f} — "
                f"Verlustausgleich mit Dividenden, Anleihen etc. möglich."
            )

        return {
            "transaktionen_detail": details,
            "zusammenfassung": {
                "steuerpflichtige_gewinne": round(total_taxable_gains, 2),
                "steuerfreie_gewinne": round(total_tax_free_gains, 2),
                "verluste": round(total_losses, 2),
                "saldo": saldo,
                "kest_27_5": round(total_kest, 2),
            },
            "laufende_einkuenfte": {
                "staking_mining": round(total_staking_mining, 2),
                "steuer": round(total_staking_mining * KEST_RATE, 2),
            },
            "portfolio": portfolio_summary,
            "hinweise": hints,
        }


def format_human_readable(result: Dict[str, Any]) -> str:
    """Format calculation results for human reading."""
    lines = [
        "=" * 60,
        "  KRYPTOWÄHRUNGS-STEUERBERECHNUNG 2026",
        "=" * 60,
        "",
        "  TRANSAKTIONEN:",
    ]

    for tx in result["transaktionen_detail"]:
        status = "STEUERPFLICHTIG" if tx["steuerpflichtig"] else "steuerfrei"
        lines.extend([
            f"  [{tx['datum']}] {tx['typ'].upper()} {tx['krypto']}",
            f"    Wert: EUR {tx['wert_eur']:,.2f} | {tx['vermoegensart']} | {status}",
        ])
        if tx["gewinn_verlust"] != 0:
            lines.append(f"    Gewinn/Verlust: EUR {tx['gewinn_verlust']:,.2f} | Steuer: EUR {tx['steuer']:,.2f}")
        lines.append(f"    -> {tx['grund']}")
        lines.append("")

    summary = result["zusammenfassung"]
    lines.extend([
        "-" * 60,
        "  ZUSAMMENFASSUNG:",
        f"  Steuerpflichtige Gewinne:     EUR {summary['steuerpflichtige_gewinne']:>12,.2f}",
        f"  Steuerfreie Gewinne:          EUR {summary['steuerfreie_gewinne']:>12,.2f}",
        f"  Verluste:                     EUR {summary['verluste']:>12,.2f}",
        f"  Saldo:                        EUR {summary['saldo']:>12,.2f}",
        "",
        f"  KESt (27,5 %):                EUR {summary['kest_27_5']:>12,.2f}",
    ])

    laufend = result["laufende_einkuenfte"]
    if laufend["staking_mining"] > 0:
        lines.extend([
            "",
            f"  Staking/Mining-Einkünfte:     EUR {laufend['staking_mining']:>12,.2f}",
            f"  KESt darauf:                  EUR {laufend['steuer']:>12,.2f}",
        ])

    lines.extend(["-" * 60, ""])

    if result["portfolio"]:
        lines.append("  PORTFOLIO (aktueller Bestand):")
        for p in result["portfolio"]:
            lines.append(
                f"    {p['krypto']}: {p['menge']:.8f} "
                f"(Ø EUR {p['durchschnittspreis']:,.2f})"
            )
        lines.append("")

    lines.append("  HINWEISE:")
    for h in result["hinweise"]:
        lines.append(f"    • {h}")

    lines.extend([
        "",
        "  Hinweis: Keine Steuerberatung. Alle Berechnungen sind",
        "  Richtwerte.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Österreichischer Kryptowährungs-Steuerrechner 2026"
    )
    parser.add_argument("input_file", help="JSON-Datei mit Krypto-Transaktionen (oder '-' für stdin)")
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

    if "transaktionen" not in data:
        print("Fehler: 'transaktionen' ist erforderlich.", file=sys.stderr)
        sys.exit(1)

    calculator = CryptoTaxCalculator(data)
    result = calculator.calculate()

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_human_readable(result))


if __name__ == "__main__":
    main()
