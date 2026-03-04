---
name: austrian-tax-advisor
description: Berechnet österreichische Steuern (ESt, KöSt, USt, KESt, ImmoESt), prüft Freibeträge und Begünstigungen, und liefert steuerliche Optimierungsvorschläge für natürliche und juristische Personen nach österreichischem Recht 2026
---

# Austrian Tax Advisor Skill

## Überblick

Produktionsreifer österreichischer Steuerberatungs-Toolkit für das Steuerjahr 2026. Basierend auf dem "1x1 der Steuern 2026" von TPA Steuerberatung. Bietet 7 Python-CLI-Tools für Steuerberechnungen, eine umfassende Wissensbasis und einen interaktiven Web-Chatbot.

**Disclaimer: Keine Steuerberatung. Alle Berechnungen sind Richtwerte. Für verbindliche Auskünfte wenden Sie sich an einen Steuerberater.**

## 5-Phasen-Workflow

### Phase 1: Scoping
- Steuerliche Situation des Mandanten erfassen
- Relevante Steuerarten identifizieren (ESt, KöSt, USt, KESt, ImmoESt)
- Rechtsform und Einkunftsarten klären
- Zeitraum und Datenbasis festlegen

### Phase 2: Analyse
- Steuerberechnungen mit den bereitgestellten Tools durchführen
- Freibeträge und Absetzbeträge prüfen (Familienbonus, GFB, IFB)
- Rechtsformvergleich erstellen (EPU vs. GmbH vs. FlexCo)
- Kleinunternehmerregelung evaluieren
- Sachbezugswerte berechnen

### Phase 3: Empfehlung
- Steueroptimierungspotenziale identifizieren
- Gewinnfreibetrag und Investitionsfreibetrag maximieren
- Benefits-Paket für Mitarbeiter optimieren
- Thesaurierung vs. Ausschüttung vergleichen
- Handlungsempfehlungen formulieren

### Phase 4: Reporting
- Steuerliche Zusammenfassung erstellen
- Rechtsformvergleich-Tabelle generieren
- Jahresplanung mit Checkliste bereitstellen
- Effektive Steuerquoten darstellen

### Phase 5: Nachverfolgung
- Unterjährige Steuerschätzungen aktualisieren
- Fristen überwachen (UVA, Jahreserklärung)
- Gesetzesänderungen berücksichtigen
- Steuerplanung für Folgejahr vorbereiten

## Tools

### 1. Einkommensteuer-Rechner (`scripts/einkommensteuer_rechner.py`)

Berechnet die österreichische ESt nach dem 7-Stufen-Tarif 2026 inkl. aller Absetzbeträge.

**Features:**
- ESt-Tarif 2026 (7 Stufen: 0 %–55 %)
- Verkehrsabsetzbetrag, AVAB/AEAB
- Familienbonus Plus (EUR 2.000/EUR 700)
- Gewinnfreibetrag (15 %, max. EUR 46.400)
- Kindermehrbetrag

```bash
python scripts/einkommensteuer_rechner.py steuerdaten.json
python scripts/einkommensteuer_rechner.py steuerdaten.json --format json
echo '{"bruttoeinkommen": 75000, "kinder": 2}' | python scripts/einkommensteuer_rechner.py -
```

### 2. Körperschaftsteuer-Rechner (`scripts/koerperschaftsteuer_rechner.py`)

Berechnet KöSt + KESt für GmbH/FlexCo mit Rechtsformvergleich.

**Features:**
- KöSt 23 %, KESt 27,5 % auf Ausschüttungen
- Mindestkörperschaftsteuer (EUR 500 GmbH/FlexCo, EUR 3.500 AG)
- Thesaurierung vs. Ausschüttung
- Vergleich GmbH vs. FlexCo vs. Einzelunternehmen

```bash
python scripts/koerperschaftsteuer_rechner.py unternehmen.json
python scripts/koerperschaftsteuer_rechner.py unternehmen.json --format json
```

### 3. Umsatzsteuer-Rechner (`scripts/umsatzsteuer_rechner.py`)

Berechnet USt-Zahllast und prüft Kleinunternehmerregelung.

**Features:**
- Steuersätze: 20 %, 13 %, 10 %, 0 %
- Kleinunternehmerregelung (EUR 55.000 + Toleranz)
- Vorsteuerabzug
- UVA-Zeitraum-Bestimmung
- Empfehlung: Option zur Regelbesteuerung

```bash
python scripts/umsatzsteuer_rechner.py umsaetze.json
python scripts/umsatzsteuer_rechner.py umsaetze.json --format json
```

### 4. Sachbezugs-Rechner (`scripts/sachbezug_rechner.py`)

Berechnet geldwerte Vorteile für Dienstnehmer.

**Features:**
- PKW-Sachbezug (CO₂-basiert: 2 %/1,5 %/0 %)
- E-Auto (steuerfrei), E-Bike
- Essensgutscheine, Öffi-Ticket, Zukunftssicherung
- Mitarbeitergewinnbeteiligung, Startup-Beteiligung
- Geschätzte Steuerbelastung DN und SV-Ersparnis AG

```bash
python scripts/sachbezug_rechner.py benefits.json
python scripts/sachbezug_rechner.py benefits.json --format json
```

### 5. Investitionsfreibetrag-Rechner (`scripts/investitionsfreibetrag_rechner.py`)

Berechnet IFB, Forschungsprämie und Gewinnfreibetrag.

**Features:**
- IFB 20 % (Standard) / 22 % (Öko)
- Max. Bemessungsgrundlage EUR 1.000.000
- Forschungsprämie 14 %
- Gewinnfreibetrag (15 %, Staffelung)
- Ausschluss-Prüfung (GWG, Gebäude, PKW, gebraucht, fossil)

```bash
python scripts/investitionsfreibetrag_rechner.py investitionen.json
python scripts/investitionsfreibetrag_rechner.py investitionen.json --format json
```

### 6. Immobilienertragsteuer-Rechner (`scripts/immobilienertragssteuer_rechner.py`)

Berechnet ImmoESt bei Grundstücksverkäufen.

**Features:**
- ImmoESt 30 % auf Veräußerungsgewinn
- Alt-/Neuvermögen-Unterscheidung (Stichtag 31.3.2012)
- Pauschalbesteuerung Altvermögen (4,2 % / 18 %)
- Hauptwohnsitzbefreiung (2 Varianten)
- Herstellerbefreiung
- Inflationsbereinigung (ab Jahr 11)

```bash
python scripts/immobilienertragssteuer_rechner.py immobilie.json
python scripts/immobilienertragssteuer_rechner.py immobilie.json --format json
```

### 7. Kryptowährungs-Steuerrechner (`scripts/krypto_steuer_rechner.py`)

Berechnet KESt auf Krypto-Gewinne mit Portfolio-Tracking.

**Features:**
- KESt 27,5 % auf Neuvermögen (ab 1.3.2021)
- Altvermögen-Regeln (Spekulationsfrist 1 Jahr)
- Krypto→Krypto-Tausch steuerfrei (Neuvermögen)
- Staking/Mining/Airdrops
- Gleitender Durchschnittspreis
- Verlustausgleich mit anderen Kapitalerträgen

```bash
python scripts/krypto_steuer_rechner.py transaktionen.json
python scripts/krypto_steuer_rechner.py transaktionen.json --format json
```

## Knowledge Base

| Datei | Inhalt |
|---|---|
| `references/steuertarif-2026.md` | ESt-Tarif (7 Stufen), Absetzbeträge, Freibeträge, SV-Werte, Sonderausgaben |
| `references/unternehmensbesteuerung-2026.md` | KöSt 23 %, MiKö, GFB, IFB, Forschungsprämie, Pauschalierung, Verlustverrechnung |
| `references/umsatzsteuer-2026.md` | USt-Sätze, Kleinunternehmerregelung, Vorsteuer, Reverse Charge, ig Lieferungen |
| `references/arbeitgeber-arbeitnehmer-2026.md` | Sachbezüge, steuerfreie Benefits, Pendlerpauschale, Lohnnebenkosten |
| `references/kapitalvermoegen-immobilien-2026.md` | KESt, Kryptobesteuerung, ImmoESt, GrESt, AfA |

## Templates

| Datei | Inhalt |
|---|---|
| `assets/steuerplanung_checkliste.md` | Jahres-Checkliste: Freibeträge, Investitionen, Benefits, Administration |
| `assets/rechtsformvergleich_template.md` | Vergleichstabelle EPU vs. GmbH vs. FlexCo mit Steuerbelastung |
| `assets/mitarbeiter_benefits_uebersicht.md` | Alle steuerfreien Benefits mit Grenzwerten und Beispielrechnung |
| `assets/sample_steuerdaten.json` | Beispiel-JSON für alle 7 Scripts |

## Zielgruppen-Adaptionen

### EPU / Freiberufler
- ESt-Rechner mit Gewinnfreibetrag
- Kleinunternehmerregelung prüfen
- Basispauschalierung evaluieren
- Arbeitsplatzpauschale

### GmbH / FlexCo
- KöSt + KESt Gesamtbelastung
- Thesaurierung vs. Ausschüttung
- Geschäftsführer-Bezüge optimieren
- Gruppenbesteuerung

### Dienstgeber
- Sachbezugs-Optimierung
- Steuerfreie Benefits-Pakete
- Lohnnebenkosten-Kalkulation
- E-Mobility (Firmenwagen)

### Arbeitnehmer
- Absetzbeträge maximieren
- Pendlerpauschale + Pendlereuro
- Familienbonus Plus
- Arbeitnehmerveranlagung

### Immobilieninvestor
- ImmoESt-Berechnung
- Hauptwohnsitzbefreiung
- AfA-Optimierung
- GrESt-Kalkulation

### Krypto-Investor
- Portfolio-Tracking
- Alt-/Neuvermögen-Klassifizierung
- Verlustausgleich
- Steuerreporting

## Schlüsselkennzahlen

| Kennzahl | Beschreibung |
|---|---|
| Effektive Steuerbelastung | Tatsächliche Steuer / Bruttoeinkommen |
| Grenzsteuersatz | Steuersatz auf den nächsten verdienten Euro |
| Gesamtabgabenquote | (Steuer + SV) / Bruttoeinkommen |
| KöSt+KESt-Quote | Gesamtbelastung GmbH bei Ausschüttung |
| USt-Zahllast | USt geschuldet − Vorsteuer |
| IFB-Steuerersparnis | IFB × Grenzsteuersatz |

## Web-Chatbot

Ein interaktiver Steuerberater-Assistent ist unter `chatbot/` verfügbar:

```bash
cd chatbot
cp .env.example .env  # ANTHROPIC_API_KEY eintragen
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
# → http://localhost:8000
```

Der Chatbot nutzt Claude API mit Tool Use, um die 7 Rechner-Scripts automatisch aufzurufen und verständliche Antworten zu liefern.
