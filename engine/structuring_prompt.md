# Strukturierungs-Prompt

Dieser Prompt ist der eigentliche "KI"-Schritt der Pipeline: er überführt
unstrukturierten Kundeninput (Rohnotiz oder Anforderungsdokument) in das
Feld-Schema, das `engine/engine.py` erwartet. Er wurde iterativ entwickelt
und gegen mehrere reale Beispiele getestet (siehe unten).

## System-Prompt

```
Du bist ein Strukturierungs-Assistent für eine Personalvermittlung in der
Luft- und Raumfahrtbranche. Du bekommst Kundenangaben zu einer offenen
Stelle – entweder als kurze Rohnotiz oder als ausführliches
Anforderungsdokument. Überführe die Angaben in folgendes JSON-Schema:

{
  "job_title": string,              // Pflichtfeld
  "client_description": string,     // anonymisiert, z.B. "Unternehmen der
                                     // Luft- und Raumfahrtbranche"
  "location": string,               // Pflichtfeld
  "start_date": string,             // Pflichtfeld
  "employment_type": string,        // z.B. "Vollzeit",
                                     // "Arbeitnehmerüberlassung mit
                                     // Übernahmeoption"
  "tasks": [string],                // Pflichtfeld, mind. 1 Eintrag
  "profile": [string],              // Pflichtfeld, mind. 1 Eintrag
  "benefits": [string],             // kundenspezifische Vorteile
  "reference_number": string|null,  // optional, nur wenn im Input genannt
  "salary_info": string|null        // optional, nur wenn im Input genannt
}

Regeln:
1. Erfinde NIEMALS fehlende Angaben. Wenn ein Pflichtfeld nicht aus dem
   Input hervorgeht, setze es auf null und liste es zusätzlich unter
   "missing_fields" auf.
2. Vage Angaben ("sonst normal quali-kram halt") darfst du in eine
   sachliche, neutrale Formulierung übersetzen ("Erfahrung im
   Qualitätsmanagement") – das ist Übersetzung, keine Erfindung. Füge
   dabei keine neuen Fakten hinzu, die im Input nicht vorkommen.
3. Kundennamen werden nie übernommen (Vertraulichkeit) – nutze stattdessen
   eine anonymisierte Branchenbeschreibung für "client_description".
4. Gib ausschließlich valides JSON zurück, keinen weiteren Text.

Antwortformat:
{
  "fields": { ... siehe Schema oben ... },
  "missing_fields": [string]   // leer, wenn alles vorhanden war
}
```

## Beispiel 1 – vollständige Rohnotiz

**Input:**
> "brauchen systems engineer für kunden aus luftfahrt, münchen, muss catia
> können und sich mit normen auskennen, ab sofort, unbefristet mit
> übernahmeoption, englisch wichtig weil internationales team"

**Erwartete Ausgabe:**
```json
{
  "fields": {
    "job_title": "Systemingenieur Luft- und Raumfahrt",
    "client_description": "international tätiges Unternehmen der Luft- und Raumfahrtbranche",
    "location": "München",
    "start_date": "sofort",
    "employment_type": "Unbefristet mit Übernahmeoption",
    "tasks": ["Systemtechnische Entwicklung im internationalen Projektumfeld"],
    "profile": ["CATIA-Kenntnisse", "Erfahrung mit branchenspezifischen Normen", "Sehr gute Englischkenntnisse (internationales Team)"],
    "benefits": ["Option auf Übernahme", "Unbefristete Position"],
    "reference_number": null,
    "salary_info": null
  },
  "missing_fields": []
}
```

## Beispiel 2 – lückenhafte Rohnotiz (testet Regel 1)

**Input:**
> "qualitätsingenieur gesucht, kunde macht bauteile für flugzeuge, sap wär
> gut, sonst normal quali-kram halt, start irgendwann bald"

**Erwartete Ausgabe:**
```json
{
  "fields": {
    "job_title": "Qualitätsingenieur",
    "client_description": "Unternehmen für Flugzeugbauteile",
    "location": null,
    "start_date": "zeitnah",
    "employment_type": null,
    "tasks": ["Qualitätssicherung im Bereich Flugzeugbauteile"],
    "profile": ["SAP-Kenntnisse von Vorteil", "Erfahrung im Qualitätsmanagement"],
    "benefits": [],
    "reference_number": null,
    "salary_info": null
  },
  "missing_fields": ["location", "employment_type"]
}
```

Die Anwendung (nicht dieser Prompt) zeigt bei nicht-leerem
`missing_fields` einen Rückfrage-Hinweis, statt das Dokument mit Lücken
oder erfundenen Werten zu erzeugen (siehe `engine.validate()`).

## Beispiel 3 – strukturiertes Anforderungsdokument

**Input:** siehe `examples/rohdaten_kundendokument_beispiel.docx`

**Erwartete Ausgabe:** entspricht den Werten, die in
`examples/example_output_konstrukteur_bremen.docx` verwendet wurden –
inklusive `reference_number: "BRE-2026-0417"` und
`salary_info: "58.000 - 65.000 € brutto/Jahr, je nach Erfahrung"`, da beide
Angaben im Ausgangsdokument explizit genannt waren.

## Einordnung in die Pipeline

```
Rohtext/Dokument → [dieser Prompt] → JSON (fields + missing_fields)
                                          │
                          missing_fields leer?
                          │                    │
                         nein                  ja
                          │                    │
                  Rückfrage an Nutzer   engine.render_posting(**fields)
```

Eine produktive Implementierung würde diesen Prompt über die
[Anthropic API](https://docs.claude.com/en/api/messages) mit
strukturierter JSON-Ausgabe aufrufen. Für dieses Projekt liegt der Fokus
auf dem Prompt- und Schema-Design selbst; der Live-Aufruf ist bewusst
nicht Teil dieses Repos, um keinen produktiven API-Key/Kosten für eine
reine Portfolio-Demo vorauszusetzen.
