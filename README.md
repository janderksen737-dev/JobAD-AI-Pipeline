# KI-gestützte Automatisierungspipeline für Stellenanzeigen

Privates Entwicklungsprojekt von Jan Derksen (2026).

Automatisiert den Weg von unstrukturierten Kundenanfragen (rohe Notizen einer
Personalvermittlung) bis zur fertigen, professionellen Stellenanzeige –
inklusive anschlussfertigem Payload für die Indeed Job Sync API.

## Ausgangslage

Personalvermittlungen erstellen Stellenanzeigen meist manuell aus
unstrukturierten Kundenangaben (Notizen, Telefonaten, kurzen E-Mails). Das
kostet Zeit, führt zu uneinheitlicher Qualität und macht die Veröffentlichung
auf Jobbörsen zu einem zusätzlichen manuellen Schritt.

## Architektur

```
Freitext (Rohnotiz)
    │
    ▼
KI-Strukturierung  →  Felder (job_title, location, tasks, profile, ...)
    │
    ▼
Validierung        →  fehlende Pflichtfelder werden zurückgemeldet, nicht erfunden
    │
    ▼
engine/engine.py   →  befüllt templates/template.docx (docxtpl)
    │
    ▼
fertige .docx-Stellenanzeige
    │
    ▼
indeed_integration/indeed_client.py  →  Payload im offiziellen
                                        Indeed-Job-Sync-API-Format (GraphQL)
```

## Projektstruktur

```
engine/                  Rendering-Engine (docxtpl-basiert)
templates/                Word-Vorlage + Logo + Icons (eigenes Design,
                           recherchebasiert auf aktuelle Best Practices für
                           Stellenanzeigen)
indeed_integration/        Payload-Generator + Mock-Server für die
                           Indeed Job Sync API
examples/                  Beispiel-Output (befüllte Stellenanzeigen)
```

## Beispiel

**Vorher (Rohnotiz):**
> "brauchen dringend jemanden für avionik-systemtest bei kunde in hamburg,
> sicherheitsüberprüfung ist pflicht (Ü2), mind. 5 jahre berufserfahrung,
> kenntnisse in DO-178C und matlab/simulink zwingend, start august"

**Nachher (generiert):** siehe `examples/example_output_avionik.docx`

## Verwendung

```bash
pip install -r requirements.txt

# Stellenanzeige aus strukturierten Daten erzeugen
python engine/engine.py

# Indeed-Payload bauen und gegen lokalen Mock-Endpunkt testen
python indeed_integration/indeed_client.py
```

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
