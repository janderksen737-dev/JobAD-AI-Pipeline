# Neuen Kunden anlegen

Fuer jeden Personalvermittlungs-Kunden gibt es einen eigenen Ordner unter `clients/<slug>/` mit
einer `config.yaml`. `talentbridge_demo/` ist die Referenz (die urspruengliche Demo-Agentur).

## Schritte

1. Ordner kopieren: `clients/talentbridge_demo/` -> `clients/<neuer_slug>/`
   (Slug nur Buchstaben, Ziffern, `_` und `-` — wird auch als CLI-Parameter und Ordnername verwendet)
2. `config.yaml` anpassen:
   - `agency`: echte Kontaktdaten der Vermittlung
   - `template.docx_path` / `template.logo_path`: eigenes Word-Template + Logo hinterlegen
     (relativ zum Repo-Root), falls der Kunde ein eigenes Layout will — sonst das Standard-Template
     aus `templates/` weiterverwenden
   - `standard_benefits`: Standard-Vorteile, die auf (fast) jeder Anzeige dieses Kunden stehen sollen
   - `industry_context`: kurzer Freitext zur Branche/Spezialisierung des Kunden. Wird dem
     KI-Strukturierungs-Prompt angehaengt, damit derselbe Prompt auch fuer Kunden ausserhalb der
     Luft- und Raumfahrtbranche sinnvolle Ergebnisse liefert
3. Testen: `python run_pipeline.py --client <neuer_slug> --job-slug test --input <rohnotiz.txt>`
