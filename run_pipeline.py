"""
Orchestriert die gesamte Pipeline fuer einen einzelnen Kunden-Auftrag:

    Freitext-Datei -> KI-Strukturierung -> Validierung
        -> Word-Anzeige (docx) -> Indeed-Payload (json)

Wird vom Betreiber manuell pro Auftrag ausgefuehrt (kein Webservice):

    python run_pipeline.py --client talentbridge_demo --job-slug avionik-hamburg \\
        --input rohnotiz.txt

Bei fehlenden Pflichtangaben werden keine Dateien geschrieben, sondern die
fehlenden Felder werden geloggt (siehe engine/structuring_prompt.md, Regel 1).
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from config.client_config import ClientConfigError, load_client_config
from engine.engine import render_posting, validate
from engine.structuring import StructuringError, structure_freetext
from indeed_integration.indeed_client import build_indeed_payload
from utils.logging_setup import setup_logging
from utils.paths import resolve_output_dir, safe_slug

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_BASE = REPO_ROOT / "output"

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RecruitFlow-Pipeline fuer einen Auftrag ausfuehren.")
    parser.add_argument("--client", required=True, help="Kunden-Slug, siehe clients/<slug>/config.yaml")
    parser.add_argument("--job-slug", required=True, help="Kurzer Bezeichner fuer diesen Auftrag")
    parser.add_argument("--input", required=True, type=Path, help="Pfad zur Rohnotiz-Textdatei")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def run(client_slug: str, job_slug: str, input_path: Path) -> int:
    job_slug = safe_slug(job_slug, field_name="job-slug")

    try:
        client_config = load_client_config(client_slug)
    except ClientConfigError as exc:
        logger.error("Kundenkonfiguration konnte nicht geladen werden: %s", exc)
        return 1

    if not input_path.is_file():
        logger.error("Eingabedatei nicht gefunden: %s", input_path)
        return 1
    raw_text = input_path.read_text(encoding="utf-8")

    try:
        structured = structure_freetext(raw_text, client_config)
    except StructuringError as exc:
        logger.error("KI-Strukturierung fehlgeschlagen: %s", exc)
        return 1

    fields = structured.fields.model_dump()
    job_specific_benefits = fields.pop("benefits") or []
    employment_type = fields.pop("employment_type") or "Vollzeit"
    reference_number = fields.pop("reference_number") or ""
    salary_info = fields.pop("salary_info") or ""
    # verbleibend in fields: job_title, client_description, location, start_date, tasks, profile

    missing = sorted(set(structured.missing_fields) | set(validate(fields)))
    if missing:
        logger.error(
            "Pflichtangaben fehlen, es werden keine Dateien erzeugt: %s",
            ", ".join(missing),
        )
        return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    output_dir = resolve_output_dir(OUTPUT_BASE, client_slug, f"{job_slug}_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    agency = client_config.agency.model_dump()
    combined_benefits = job_specific_benefits + client_config.standard_benefits

    docx_path = output_dir / "stellenanzeige.docx"
    render_posting(
        agency=agency,
        standard_benefits=client_config.standard_benefits,
        template_path=client_config.resolved_template_path(),
        logo_path=client_config.resolved_logo_path(),
        client_specific_benefits=job_specific_benefits,
        employment_type=employment_type,
        reference_number=reference_number,
        salary_info=salary_info,
        output_path=str(docx_path),
        **fields,
    )

    payload = build_indeed_payload(
        job_title=fields["job_title"],
        employment_type=employment_type,
        location=fields["location"],
        start_date=fields["start_date"],
        tasks=fields["tasks"],
        profile=fields["profile"],
        benefits=combined_benefits,
        agency=agency,
        client_description=fields["client_description"] or "",
        job_posting_id=f"{client_slug}-{job_slug}-{timestamp}",
    )
    payload_path = output_dir / "indeed_payload.json"
    payload_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("Fertig. Ausgabe unter: %s", output_dir)
    return 0


def main() -> int:
    args = parse_args()
    setup_logging(verbose=args.verbose)
    load_dotenv()
    return run(args.client, args.job_slug, args.input)


if __name__ == "__main__":
    sys.exit(main())
