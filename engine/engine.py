"""
Engine: befüllt die Stellenanzeigen-Vorlage (templates/template.docx) mit
strukturierten Job-Daten. Nutzt docxtpl (Jinja2-Syntax direkt in Word-Platzhaltern).

Typischer Ablauf im Gesamtprojekt:
    Freitext (Kundennotiz)
        -> KI-Strukturierung in Felder (nicht Teil dieser Datei, siehe README)
        -> Validierung (fehlende Pflichtfelder werden zurückgemeldet, nicht erfunden)
        -> engine.render_posting(...)  <- diese Datei
        -> fertiges .docx
        -> indeed_integration/indeed_client.py für die Jobbörsen-Anbindung
"""
import os
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(_REPO_ROOT, "templates", "template.docx")
LOGO_PATH = os.path.join(_REPO_ROOT, "templates", "logo.png")

# Feste Vermittlungs-Anker (Beispieldaten einer fiktiven Muster-Agentur)
AGENCY = {
    "agency_name": "TalentBridge Personalvermittlung GmbH",
    "agency_street": "Musterstraße 12",
    "agency_zip_city": "80331 München",
    "agency_phone": "+49 89 1234567",
    "agency_email": "kontakt@talentbridge-beispiel.de",
    "agency_website": "www.talentbridge-beispiel.de",
    "contact_person": "Max Mustermann",
}

# Standard-Perks, die auf (fast) jeder Anzeige stehen, unabhängig vom Kunden
AGENCY_STANDARD_BENEFITS = [
    "Persönliche und individuelle Betreuung durch unser erfahrenes Berater-Team",
    "Langfristige Perspektive mit Option auf Übernahme beim Kundenunternehmen",
    "Zugang zu einem breiten Netzwerk an Unternehmen der Luft- und Raumfahrtbranche",
]

REQUIRED_FIELDS = ["job_title", "location", "tasks", "profile"]


def validate(fields: dict) -> list[str]:
    """Gibt eine Liste offener Punkte zurück, statt fehlende Angaben zu erfinden."""
    missing = []
    for f in REQUIRED_FIELDS:
        if not fields.get(f):
            missing.append(f)
    return missing


def render_posting(client_specific_benefits, employment_type="Vollzeit", reference_number="",
                    salary_info="", output_path="output.docx", **fields):
    """
    Baut eine fertige Stellenanzeige aus strukturierten Feldern.

    fields erwartet mind.: job_title, client_description, location,
    start_date, tasks (list), profile (list)

    reference_number und salary_info sind optional (professionelleres
    Erscheinungsbild, wenn der Kunde diese Angaben mitliefert – siehe
    README, Abschnitt "Erweiterte Felder").
    """
    missing = validate(fields)
    if missing:
        raise ValueError(f"Pflichtfelder fehlen, bitte ergänzen: {', '.join(missing)}")

    doc = DocxTemplate(TEMPLATE_PATH)
    title_display = f"{fields['job_title']} (m/w/d)"
    if employment_type:
        title_display += f" in {employment_type}"

    context = {
        **AGENCY,
        "agency_logo": InlineImage(doc, LOGO_PATH, width=Mm(45)),
        **fields,
        "employment_type": employment_type,
        "reference_number": reference_number,
        "salary_info": salary_info,
        "title_display": title_display,
        "benefits": client_specific_benefits + AGENCY_STANDARD_BENEFITS,
    }
    doc.render(context)
    doc.save(output_path)
    return output_path


if __name__ == "__main__":
    # Beispiel-Rohnotiz (Referenz, unstrukturiert):
    # "brauchen dringend jemanden für avionik-systemtest bei kunde in hamburg,
    #  sicherheitsüberprüfung ist pflicht (Ü2), schichtarbeit möglich (2-schicht),
    #  mind. 5 jahre berufserfahrung in der luftfahrt, kenntnisse in DO-178C
    #  und matlab/simulink zwingend, start august, vertrag 18 monate mit
    #  übernahmeoption, reisebereitschaft ca 20%"
    render_posting(
        client_specific_benefits=["18-monatiger Vertrag mit klarer Übernahmeoption"],
        job_title="Avionik-Systemtestingenieur",
        client_description="Unternehmen im Bereich Avioniksysteme",
        location="Hamburg",
        start_date="August",
        tasks=[
            "Durchführung von Systemtests an Avioniksystemen",
            "Dokumentation der Testergebnisse nach DO-178C",
            "Zusammenarbeit mit internationalen Entwicklungsteams",
        ],
        profile=[
            "Mind. 5 Jahre Berufserfahrung in der Luftfahrtbranche",
            "Zwingende Kenntnisse in DO-178C und MATLAB/Simulink",
            "Sicherheitsüberprüfung Ü2 erforderlich",
        ],
        output_path=os.path.join(_REPO_ROOT, "examples", "generated_example.docx"),
    )
    print("Anzeige erstellt: examples/generated_example.docx")

    # Zweites Beispiel: Input ist kein Notizzettel, sondern ein gut
    # strukturiertes Kundendokument (examples/rohdaten_kundendokument_beispiel.docx).
    # In der Praxis übernimmt der KI-Strukturierungsschritt (nicht Teil dieser
    # Datei, siehe README) das Auslesen; hier die daraus resultierenden Felder,
    # inkl. der zusätzlichen, aus dem Dokument stammenden Angaben
    # (Referenznummer, Gehaltsrahmen) für ein professionelleres Erscheinungsbild.
    render_posting(
        client_specific_benefits=[
            "Übernahmeoption nach Arbeitnehmerüberlassung",
        ],
        employment_type="Arbeitnehmerüberlassung mit Übernahmeoption",
        reference_number="BRE-2026-0417",
        salary_info="58.000 - 65.000 € brutto/Jahr, je nach Erfahrung",
        job_title="Konstrukteur Strukturbauteile",
        client_description="Unternehmen der Luft- und Raumfahrtbranche",
        location="Bremen",
        start_date="zum nächstmöglichen Zeitpunkt",
        tasks=[
            "Konstruktion von Strukturbauteilen in CATIA V5",
            "Erstellung und Pflege technischer Zeichnungen nach Luftfahrtnormen",
            "Abstimmung mit Stress-Engineering und Fertigung",
        ],
        profile=[
            "Abgeschlossenes Studium Maschinenbau/Luft- und Raumfahrttechnik oder vergleichbar",
            "Mind. 3 Jahre Erfahrung in der Strukturkonstruktion, idealerweise Luftfahrt",
            "Sehr gute CATIA V5-Kenntnisse",
            "Gute Deutsch- und Englischkenntnisse",
        ],
        output_path=os.path.join(_REPO_ROOT, "examples", "generated_example_from_document.docx"),
    )
    print("Anzeige erstellt: examples/generated_example_from_document.docx")
