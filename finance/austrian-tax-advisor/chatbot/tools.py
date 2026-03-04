"""Claude Tool definitions — maps each calculator script to a Claude tool."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from config import SCRIPTS_DIR


TOOLS: List[Dict[str, Any]] = [
    {
        "name": "einkommensteuer_berechnen",
        "description": (
            "Berechnet die österreichische Einkommensteuer 2026 basierend auf dem "
            "Bruttoeinkommen. Verwende dieses Tool wenn der User nach seiner Steuerlast, "
            "seinem Grenzsteuersatz oder seiner Einkommensteuer fragt."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "bruttoeinkommen": {
                    "type": "number",
                    "description": "Jährliches Bruttoeinkommen in EUR",
                },
                "abzuege": {
                    "type": "number",
                    "description": "Werbungskosten/Betriebsausgaben in EUR",
                    "default": 0,
                },
                "kinder": {
                    "type": "integer",
                    "description": "Anzahl der Kinder (unter 18) für Familienbonus Plus",
                    "default": 0,
                },
                "kinder_ueber_18": {
                    "type": "integer",
                    "description": "Anzahl der Kinder über 18 Jahre",
                    "default": 0,
                },
                "alleinverdiener": {
                    "type": "boolean",
                    "description": "Alleinverdienerabsetzbetrag anwendbar",
                    "default": False,
                },
                "alleinerzieher": {
                    "type": "boolean",
                    "description": "Alleinerzieherabsetzbetrag anwendbar",
                    "default": False,
                },
                "pendlerpauschale": {
                    "type": "number",
                    "description": "Jährliche Pendlerpauschale in EUR",
                    "default": 0,
                },
            },
            "required": ["bruttoeinkommen"],
        },
    },
    {
        "name": "koerperschaftsteuer_berechnen",
        "description": (
            "Berechnet die Gesamtsteuerbelastung für GmbH/FlexCo (KöSt + KESt auf "
            "Ausschüttungen). Verwende dieses Tool bei Fragen zu Unternehmensbesteuerung, "
            "Rechtsformvergleich, Thesaurierung vs. Ausschüttung."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gewinn": {
                    "type": "number",
                    "description": "Jahresgewinn vor Steuern in EUR",
                },
                "ausschuettung_prozent": {
                    "type": "number",
                    "description": "Anteil des Gewinns der ausgeschüttet wird (0-100)",
                    "default": 100,
                },
                "rechtsform": {
                    "type": "string",
                    "enum": ["gmbh", "flexco", "einzelunternehmen"],
                    "description": "Rechtsform des Unternehmens",
                    "default": "gmbh",
                },
                "verlustvortraege": {
                    "type": "number",
                    "description": "Vorhandene Verlustvorträge in EUR",
                    "default": 0,
                },
            },
            "required": ["gewinn"],
        },
    },
    {
        "name": "umsatzsteuer_berechnen",
        "description": (
            "Berechnet die Umsatzsteuer-Zahllast und prüft die Kleinunternehmerregelung. "
            "Verwende bei Fragen zu USt, Vorsteuer, Kleinunternehmer-Grenze."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "umsaetze": {
                    "type": "array",
                    "description": "Liste der Umsätze mit Bezeichnung, Nettobetrag und Steuersatz",
                    "items": {
                        "type": "object",
                        "properties": {
                            "bezeichnung": {"type": "string"},
                            "netto": {"type": "number"},
                            "steuersatz": {"type": "integer", "enum": [0, 10, 13, 20]},
                        },
                        "required": ["netto", "steuersatz"],
                    },
                },
                "vorsteuer": {
                    "type": "number",
                    "description": "Vorsteuer aus Eingangsrechnungen in EUR",
                    "default": 0,
                },
            },
            "required": ["umsaetze"],
        },
    },
    {
        "name": "sachbezug_berechnen",
        "description": (
            "Berechnet Sachbezugswerte für Dienstnehmer (PKW, Benefits, Essensgutscheine). "
            "Verwende bei Fragen zu Firmenwagenbesteuerung oder Mitarbeiter-Benefits."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dienstwagen": {
                    "type": "object",
                    "description": "Firmenwagen-Daten",
                    "properties": {
                        "listenpreis": {"type": "number", "description": "Brutto-Listenpreis in EUR"},
                        "co2_emission": {"type": "integer", "description": "CO2 in g/km (WLTP)"},
                        "ist_elektro": {"type": "boolean", "default": False},
                        "privat_km_monat": {"type": "integer", "default": 501},
                    },
                },
                "benefits": {
                    "type": "array",
                    "description": "Liste der Mitarbeiter-Benefits",
                    "items": {
                        "type": "object",
                        "properties": {
                            "typ": {
                                "type": "string",
                                "enum": [
                                    "zukunftssicherung", "mitarbeiterrabatt",
                                    "essensgutscheine_gaststaette", "essensgutscheine_lebensmittel",
                                    "oeffi_ticket", "kinderbetreuung", "gewinnbeteiligung",
                                    "startup_beteiligung", "betriebsveranstaltung",
                                    "weihnachtsgeschenk", "e_bike", "carsharing",
                                ],
                            },
                            "betrag": {"type": "number"},
                            "tage": {"type": "integer"},
                        },
                        "required": ["typ"],
                    },
                },
            },
        },
    },
    {
        "name": "investitionsfreibetrag_berechnen",
        "description": (
            "Berechnet den Investitionsfreibetrag und die Forschungsprämie. "
            "Verwende bei Fragen zu Investitionsförderungen oder Steuerbegünstigungen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "investitionen": {
                    "type": "array",
                    "description": "Liste der Investitionen",
                    "items": {
                        "type": "object",
                        "properties": {
                            "bezeichnung": {"type": "string"},
                            "betrag": {"type": "number"},
                            "kategorie": {
                                "type": "string",
                                "enum": ["standard", "oeko", "gebraucht", "gwg",
                                         "grundstueck", "gebaeude", "pkw_verbrenner", "fossil"],
                            },
                        },
                        "required": ["betrag", "kategorie"],
                    },
                },
                "gewinn": {
                    "type": "number",
                    "description": "Jahresgewinn in EUR",
                    "default": 0,
                },
                "forschungsaufwendungen": {
                    "type": "number",
                    "description": "F&E-Aufwendungen in EUR",
                    "default": 0,
                },
            },
            "required": ["investitionen"],
        },
    },
    {
        "name": "immobilienertragssteuer_berechnen",
        "description": (
            "Berechnet die Immobilienertragsteuer bei Grundstücksverkäufen. "
            "Verwende bei Fragen zu Immobilienverkauf, Spekulationssteuer, Hauptwohnsitzbefreiung."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "kaufdatum": {"type": "string", "description": "Kaufdatum (YYYY-MM-DD)"},
                "kaufpreis": {"type": "number", "description": "Kaufpreis in EUR"},
                "verkaufspreis": {"type": "number", "description": "Verkaufspreis in EUR"},
                "verkaufsdatum": {"type": "string", "description": "Verkaufsdatum (YYYY-MM-DD)", "default": "2026-03-01"},
                "ist_hauptwohnsitz": {"type": "boolean", "default": False},
                "hauptwohnsitz_jahre": {"type": "number", "default": 0},
                "instandsetzungskosten": {"type": "number", "default": 0},
                "nebenkosten_kauf": {"type": "number", "default": 0},
                "nebenkosten_verkauf": {"type": "number", "default": 0},
            },
            "required": ["kaufpreis", "verkaufspreis"],
        },
    },
    {
        "name": "krypto_steuer_berechnen",
        "description": (
            "Berechnet die Besteuerung von Kryptowährungsgewinnen. "
            "Verwende bei Fragen zu Bitcoin/Krypto-Steuern, Altvermögen, Staking."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transaktionen": {
                    "type": "array",
                    "description": "Liste der Krypto-Transaktionen",
                    "items": {
                        "type": "object",
                        "properties": {
                            "typ": {
                                "type": "string",
                                "enum": ["kauf", "verkauf", "tausch", "staking", "mining", "airdrop"],
                            },
                            "datum": {"type": "string", "description": "Datum (YYYY-MM-DD)"},
                            "krypto": {"type": "string", "description": "Kryptowährung (z.B. BTC, ETH)"},
                            "menge": {"type": "number"},
                            "preis_eur": {"type": "number", "description": "Gesamtpreis in EUR"},
                            "krypto_von": {"type": "string"},
                            "krypto_nach": {"type": "string"},
                            "wert_eur": {"type": "number"},
                        },
                        "required": ["typ", "datum"],
                    },
                },
            },
            "required": ["transaktionen"],
        },
    },
]

# Map tool names to script files
TOOL_SCRIPT_MAP: Dict[str, str] = {
    "einkommensteuer_berechnen": "einkommensteuer_rechner.py",
    "koerperschaftsteuer_berechnen": "koerperschaftsteuer_rechner.py",
    "umsatzsteuer_berechnen": "umsatzsteuer_rechner.py",
    "sachbezug_berechnen": "sachbezug_rechner.py",
    "investitionsfreibetrag_berechnen": "investitionsfreibetrag_rechner.py",
    "immobilienertragssteuer_berechnen": "immobilienertragssteuer_rechner.py",
    "krypto_steuer_berechnen": "krypto_steuer_rechner.py",
}


def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Execute a calculator script and return the JSON result."""
    script_name = TOOL_SCRIPT_MAP.get(tool_name)
    if not script_name:
        return json.dumps({"error": f"Unbekanntes Tool: {tool_name}"})

    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        return json.dumps({"error": f"Script nicht gefunden: {script_path}"})

    # Write input to temp file
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(tool_input, tmp, ensure_ascii=False)
            tmp_path = tmp.name

        # Run the script
        result = subprocess.run(
            [sys.executable, str(script_path), tmp_path, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
        )

        if result.returncode != 0:
            return json.dumps({
                "error": f"Script-Fehler: {result.stderr.strip()}",
            })

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Script-Timeout (30s)"})
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass
