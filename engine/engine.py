"""
Engine: befüllt die Stellenanzeigen-Vorlage mit strukturierten Job-Daten.
Nutzt docxtpl (Jinja2-Syntax direkt in Word-Platzhaltern).

Typischer Ablauf im Gesamtprojekt:
    Freitext (Kundennotiz)
        -> KI-Strukturierung in Felder (engine/structuring.py)
        -> Validierung (fehlende Pflichtfelder werden zurückgemeldet, nicht erfunden)
        -> engine.render_posting(...)  <- diese Datei
        -> fertiges .docx
        -> indeed_integration/indeed_client.py für die Jobbörsen-Anbindung

Agentur-Identität, Standard-Benefits und Vorlagenpfade sind seit der
Mehrmandantenfähigkeit nicht mehr hier fest einprogrammiert, sondern kommen
pro Kunde aus clients/<slug>/config.yaml (siehe config/client_config.py).
"""
import logging
import os
import re

from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Erkennt eine bereits vorhandene Gender-Endung am Ende des Jobtitels (z.B. von der
# KI-Strukturierung schon angehaengt), damit sie nicht doppelt erscheint - deckt die
# gaengigen Reihenfolgen/Trenner ab (m/w/d, w/m/d, m/w/x, d/m/w, mit "-" oder "/").
_GENDER_SUFFIX_RE = re.compile(r"\s*\([mwdx](?:[/-][mwdx]){1,2}\)\s*$", re.IGNORECASE)

# Pflichtfelder gemaess dem Schema in engine/structuring_prompt.md.
# start_date ist dort explizit als Pflichtfeld markiert.
REQUIRED_FIELDS = ["job_title", "location", "start_date", "tasks", "profile"]


def validate(fields: dict) -> list[str]:
    """Gibt eine Liste offener Punkte zurück, statt fehlende Angaben zu erfinden."""
    missing = []
    for f in REQUIRED_FIELDS:
        if not fields.get(f):
            missing.append(f)
    return missing


def render_posting(
    agency: dict,
    standard_benefits: list[str],
    template_path: str | os.PathLike,
    logo_path: str | os.PathLike,
    client_specific_benefits: list[str],
    employment_type: str = "",
    reference_number: str = "",
    salary_info: str = "",
    output_path: str = "output.docx",
    **fields,
):
    """
    Baut eine fertige Stellenanzeige aus strukturierten Feldern.

    agency: dict mit agency_name, agency_street, agency_zip_city, agency_phone,
        agency_email, agency_website, contact_person (siehe config/client_config.py)
    standard_benefits: Vorteile, die auf (fast) jeder Anzeige dieses Kunden stehen
    template_path / logo_path: Pfade zu Word-Vorlage und Logo dieses Kunden

    fields erwartet mind.: job_title, client_description, location,
    start_date, tasks (list), profile (list)

    reference_number und salary_info sind optional (professionelleres
    Erscheinungsbild, wenn der Kunde diese Angaben mitliefert – siehe
    README, Abschnitt "Erweiterte Felder").
    """
    missing = validate(fields)
    if missing:
        raise ValueError(f"Pflichtfelder fehlen, bitte ergänzen: {', '.join(missing)}")

    doc = DocxTemplate(template_path)
    job_title_clean = _GENDER_SUFFIX_RE.sub("", fields["job_title"])
    title_display = f"{job_title_clean} (m/w/d)"
    if employment_type:
        title_display += f" in {employment_type}"

    context = {
        **agency,
        "agency_logo": InlineImage(doc, str(logo_path), width=Mm(45)),
        **fields,
        "employment_type": employment_type,
        "reference_number": reference_number,
        "salary_info": salary_info,
        "title_display": title_display,
        "job_title_clean": job_title_clean,
        "benefits": client_specific_benefits + standard_benefits,
    }
    doc.render(context)
    doc.save(output_path)
    logger.info("Anzeige erstellt: %s", output_path)
    return output_path


if __name__ == "__main__":
    import sys

    sys.path.insert(0, _REPO_ROOT)
    from config.client_config import load_client_config
    from utils.logging_setup import setup_logging

    setup_logging()
    client_config = load_client_config("talentbridge_demo")
    agency = client_config.agency.model_dump()
    template_path = client_config.resolved_template_path()
    logo_path = client_config.resolved_logo_path()

    # Beispiel-Rohnotiz (Referenz, unstrukturiert):
    # "brauchen dringend jemanden für avionik-systemtest bei kunde in hamburg,
    #  sicherheitsüberprüfung ist pflicht (Ü2), schichtarbeit möglich (2-schicht),
    #  mind. 5 jahre berufserfahrung in der luftfahrt, kenntnisse in DO-178C
    #  und matlab/simulink zwingend, start august, vertrag 18 monate mit
    #  übernahmeoption, reisebereitschaft ca 20%"
    render_posting(
        agency=agency,
        standard_benefits=client_config.standard_benefits,
        template_path=template_path,
        logo_path=logo_path,
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

    # Zweites Beispiel: Input ist kein Notizzettel, sondern ein gut
    # strukturiertes Kundendokument (examples/rohdaten_kundendokument_beispiel.docx).
    # In der Praxis übernimmt der KI-Strukturierungsschritt (engine/structuring.py)
    # das Auslesen; hier die daraus resultierenden Felder, inkl. der
    # zusätzlichen, aus dem Dokument stammenden Angaben (Referenznummer,
    # Gehaltsrahmen) für ein professionelleres Erscheinungsbild.
    render_posting(
        agency=agency,
        standard_benefits=client_config.standard_benefits,
        template_path=template_path,
        logo_path=logo_path,
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
