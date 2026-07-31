# KI-gestützte Automatisierungspipeline für Stellenanzeigen

Privates Entwicklungsprojekt von Jan Derksen (2026).

Automatisiert den Weg von Kundenanfragen (von der kurzen Notiz bis zum
vollständigen Anforderungsdokument) bis zur fertigen, professionellen
Stellenanzeige – inklusive anschlussfertigem Payload für die Indeed Job
Sync API.

## Motivation

Die Idee zu diesem Projekt stammt aus eigener Erfahrung in der
Personalvermittlung: die Erstellung von Stellenanzeigen aus Kundenangaben
ist ein wiederkehrender, weitgehend manueller Prozess – unabhängig davon,
ob die Angaben als kurze Notiz oder als ausführliches Anforderungsdokument
vorliegen. Dieses Projekt ist der Versuch, diese im echten Arbeitsalltag
erkannte Ineffizienz konkret zu lösen, statt sie nur zu beobachten.

## Ausgangslage

Personalvermittlungen erhalten Kundenanfragen in ganz unterschiedlicher
Qualität – von der knappen Notiz bis zum sauber strukturierten
Anforderungsdokument. So oder so bleibt die Übertragung in eine fertige,
professionelle Stellenanzeige bislang ein manueller Schritt, der Zeit
kostet und zu uneinheitlicher Qualität führt.

## Architektur

```
Freitext (Rohnotiz)
    │
    ▼
engine/structuring.py  →  KI-Strukturierung via Anthropic API (Tool-Use,
    │                     schema-validiert) → Felder (job_title, location,
    │                     tasks, profile, ...). Prompt/Schema/Beispiele:
    │                     engine/structuring_prompt.md
    ▼
Validierung        →  fehlende Pflichtfelder werden zurückgemeldet, nicht erfunden
    │
    ▼
engine/engine.py   →  befüllt das Kunden-Template (docxtpl)
    │
    ▼
fertige .docx-Stellenanzeige
    │
    ▼
indeed_integration/indeed_client.py  →  Payload im offiziellen
                                        Indeed-Job-Sync-API-Format (GraphQL)
```

Orchestriert wird das alles von `run_pipeline.py` (ein Auftrag pro Aufruf,
siehe "Verwendung" unten) — kein Webservice, der Betreiber führt die
Pipeline manuell pro Kundenauftrag aus.

## Projektstruktur

```
run_pipeline.py            Orchestrator: ein CLI-Aufruf pro Kundenauftrag
engine/                    Rendering-Engine (docxtpl-basiert), structuring.py
                           (Anthropic-API-Anbindung) + structuring_prompt.md
                           (der KI-Strukturierungs-Prompt, Schema, Beispiele)
clients/                   Pro-Kunde-Konfiguration (Agentur-Identität,
                           Template, Standard-Benefits) – siehe clients/README.md
config/                    Laedt/validiert clients/<slug>/config.yaml
utils/                     Logging-Setup, Pfad-Sicherheit (Slug-Validierung)
templates/                 Standard-Word-Vorlage + Logo + Icons (eigenes
                           Design, recherchebasiert)
indeed_integration/        Payload-Generator + Mock-Server für die
                           Indeed Job Sync API
examples/                  Beispiel-Output (befüllte Stellenanzeigen)
tests/                     pytest-Suite (keine echten API-Aufrufe/Ports)
```

## Beispiele

**Beispiel 1 – kurze Rohnotiz als Input:**
> "brauchen dringend jemanden für avionik-systemtest bei kunde in hamburg,
> sicherheitsüberprüfung ist pflicht (Ü2), mind. 5 jahre berufserfahrung,
> kenntnisse in DO-178C und matlab/simulink zwingend, start august"

→ `examples/example_output_avionik.docx`

**Beispiel 2 – gut strukturiertes Kundendokument als Input:**
Nicht jede Anfrage kommt als knappe Notiz – gerade in der Luft- und
Raumfahrtbranche liefern Kunden häufig bereits ausführliche
Anforderungsdokumente. Die Pipeline verarbeitet auch diesen Fall:

- Rohdaten-Input: `examples/rohdaten_kundendokument_beispiel.docx`
- Ergebnis: `examples/example_output_konstrukteur_bremen.docx`

Da das Ausgangsdokument bereits Gehaltsrahmen und interne Referenznummer
enthielt, übernimmt die Engine diese zusätzlich in die erweiterten Felder
(siehe unten) – das Ergebnis wirkt dadurch spürbar professioneller als bei
einer knappen Notiz ohne diese Angaben.

## Erweiterte Felder

Optional, werden nur angezeigt, wenn vorhanden (kein erfundener Platzhalter):

- `reference_number` – interne Referenznummer, erscheint dezent im Footer
- `salary_info` – Gehaltsrahmen, erscheint in der Kopfzeile (Gehaltstransparenz
  ist eines der wichtigsten Entscheidungskriterien für Bewerber:innen)

## Verwendung

```bash
pip install -r requirements-dev.txt   # oder requirements.txt ohne Tests

cp .env.example .env                  # ANTHROPIC_API_KEY eintragen

# Kompletten Auftrag ausführen: Freitext -> Anzeige + Indeed-Payload
python run_pipeline.py --client talentbridge_demo --job-slug avionik-hamburg \
    --input rohnotiz.txt
# Ergebnis unter output/talentbridge_demo/avionik-hamburg_<timestamp>/

# Einzelne Bausteine weiterhin standalone lauffähig (Demo-/Regressionszweck):
python engine/engine.py
python indeed_integration/indeed_client.py

# Tests
pytest -q
```

Neuen Kunden anlegen: siehe [`clients/README.md`](clients/README.md).

**Hinweis zu weiteren Jobbörsen:** aktuell ist nur Indeed angebunden. Ein
zweites Board (z.B. StepStone) ist bewusst noch nicht gebaut — deren
Zugang zu einer Self-Service-Posting-API ist ungeklärt (anders als bei
Indeed) und müsste zuerst recherchiert werden.

## Technischer Umfang

- Content-Strukturierung mit Validierungslogik (fehlende Felder werden
  erkannt, nicht erfunden)
- Eigenes, recherchebasiertes Vorlagen-Design (Word-Automatisierung via
  docxtpl, inkl. Bild-/Logo-Handling und bedingten Textblöcken)
- SEO-optimierte Formulierungen (Keyword-Wiederholung, strukturierte Titel)
- Payload-Generator im offiziellen
  [Indeed-Job-Sync-API-Schema](https://docs.indeed.com/job-sync-api/) (GraphQL),
  inkl. Validierung und Fehlerbehandlung, gegen Mock-Endpunkt getestet

## Hinweis zur Indeed-Integration

Die Indeed Job Sync API ist ausschließlich für zugelassene ATS-Partner
zugänglich (kein Self-Service-API-Key). Der Payload-Generator in diesem
Repo erzeugt Requests im exakten, offiziellen Schema und wird gegen einen
lokalen Mock-Endpunkt getestet, der Indeeds Antwortverhalten (inkl.
Validierungsfehlern) nachbildet. Eine produktive Freischaltung würde einen
Indeed-Partnerstatus voraussetzen – ein Geschäftsprozess außerhalb der
Entwicklungsarbeit.

## Kontakt

Jan Derksen · jan.derksen737@gmail.com
