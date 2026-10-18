"""
Web-Oberflaeche fuer die Job-Ad-Pipeline — Prototyp.

Duenner Wrapper um dieselbe, bereits getestete Pipeline-Logik wie run_pipeline.py
(engine.structuring, engine.engine, indeed_integration.indeed_client). Keine
eigene Logik dupliziert - wenn sich die CLI-Logik aendert, bleibt dieser
Prototyp automatisch synchron, weil er dieselben Funktionen aufruft.

Start:
    cd webapp && .venv/bin/flask --app app run --debug

Ausdruecklich ein Prototyp fuer Tests, kein produktiver Webservice (kein
Hosting, keine Nutzerkonten) - siehe MASTERPLAN.md, Wachstumsbedingungen.
"""
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, send_from_directory, url_for

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from config.client_config import CLIENTS_DIR, ClientConfigError, load_client_config  # noqa: E402
from engine.engine import render_posting, validate  # noqa: E402
from engine.structuring import StructuringError, structure_freetext  # noqa: E402
from indeed_integration.indeed_client import build_indeed_payload  # noqa: E402
from utils.logging_setup import setup_logging  # noqa: E402
from utils.paths import resolve_output_dir, safe_slug  # noqa: E402

OUTPUT_BASE = REPO_ROOT / "output"

setup_logging()
load_dotenv(REPO_ROOT / ".env")
logger = logging.getLogger(__name__)

app = Flask(__name__)


@dataclass
class JobResult:
    output_dir: Path
    fields: dict
    docx_name: str
    payload_name: str


class MissingFieldsError(Exception):
    def __init__(self, missing: list[str]):
        self.missing = missing


def list_client_slugs() -> list[str]:
    if not CLIENTS_DIR.is_dir():
        return []
    return sorted(p.name for p in CLIENTS_DIR.iterdir() if (p / "config.yaml").is_file())


def _list_to_text(items: list[str]) -> str:
    return "\n".join(items)


def _text_to_list(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def structure_job(client_slug: str, raw_text: str) -> dict:
    """Erster Schritt: Freitext -> strukturierte Felder, noch keine Dateien.
    Wirft MissingFieldsError, wenn die KI-Strukturierung selbst schon Luecken meldet -
    fuer offensichtlich unvollstaendige Notizen, bevor der Mensch ueberhaupt pruefen muss."""
    client_config = load_client_config(client_slug)  # kann ClientConfigError werfen
    structured = structure_freetext(raw_text, client_config)  # kann StructuringError werfen

    fields = structured.fields.model_dump()
    job_specific_benefits = fields.pop("benefits") or []
    employment_type = fields.pop("employment_type") or ""
    reference_number = fields.pop("reference_number") or ""
    salary_info = fields.pop("salary_info") or ""

    missing = sorted(set(structured.missing_fields) | set(validate(fields)))
    if missing:
        raise MissingFieldsError(missing)

    return {
        "fields": fields,
        "job_specific_benefits": job_specific_benefits,
        "employment_type": employment_type,
        "reference_number": reference_number,
        "salary_info": salary_info,
    }


def finalize_job(client_slug: str, fields: dict, job_specific_benefits: list[str],
                  employment_type: str, reference_number: str, salary_info: str) -> JobResult:
    """Zweiter Schritt, nach der Freigabe: schreibt Dateien erst jetzt, nicht vorher.
    Prueft die Pflichtfelder erneut - falls die Freigabe ein Feld leergemacht hat, wirft
    das dieselbe MissingFieldsError wie beim ersten Durchlauf, statt eine unvollstaendige
    Anzeige zu erzeugen."""
    client_config = load_client_config(client_slug)  # kann ClientConfigError werfen

    missing = validate(fields)
    if missing:
        raise MissingFieldsError(missing)

    job_slug = safe_slug(f"web-{datetime.now(timezone.utc).strftime('%H%M%S')}", field_name="job-slug")
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

    display_fields = {**fields, "employment_type": employment_type,
                       "reference_number": reference_number, "salary_info": salary_info,
                       "benefits": combined_benefits}
    return JobResult(output_dir=output_dir, fields=display_fields,
                      docx_name=docx_path.name, payload_name=payload_path.name)


def _review_context(client_slug: str, fields: dict, job_specific_benefits: list[str],
                     employment_type: str, reference_number: str, salary_info: str,
                     raw_text: str = "", error: str = ""):
    return dict(
        client_slug=client_slug,
        fields=fields,
        tasks_text=_list_to_text(fields.get("tasks", [])),
        profile_text=_list_to_text(fields.get("profile", [])),
        benefits_text=_list_to_text(job_specific_benefits),
        employment_type=employment_type,
        reference_number=reference_number,
        salary_info=salary_info,
        raw_text=raw_text,
        error=error,
    )


@app.route("/", methods=["GET"])
def form():
    return render_template("form.html", clients=list_client_slugs())


@app.route("/generate", methods=["POST"])
def generate():
    client_slug = request.form.get("client", "")
    raw_text = request.form.get("raw_text", "")

    if not client_slug or not raw_text.strip():
        return render_template("form.html", clients=list_client_slugs(),
                                error="Bitte Kunde auswaehlen und Text eingeben.")

    try:
        structured = structure_job(client_slug, raw_text)
    except MissingFieldsError as exc:
        return render_template("missing_fields.html", missing=exc.missing, raw_text=raw_text,
                                client_slug=client_slug)
    except ClientConfigError as exc:
        return render_template("form.html", clients=list_client_slugs(), error=f"Kundenkonfiguration: {exc}")
    except StructuringError as exc:
        return render_template("form.html", clients=list_client_slugs(), error=f"KI-Strukturierung fehlgeschlagen: {exc}")

    return render_template("review.html", **_review_context(client_slug, raw_text=raw_text, **structured))


@app.route("/confirm", methods=["POST"])
def confirm():
    client_slug = request.form.get("client_slug", "")
    raw_text = request.form.get("raw_text", "")
    fields = {
        "job_title": request.form.get("job_title", "").strip(),
        "client_description": request.form.get("client_description", "").strip(),
        "location": request.form.get("location", "").strip(),
        "start_date": request.form.get("start_date", "").strip(),
        "tasks": _text_to_list(request.form.get("tasks", "")),
        "profile": _text_to_list(request.form.get("profile", "")),
    }
    job_specific_benefits = _text_to_list(request.form.get("benefits", ""))
    employment_type = request.form.get("employment_type", "").strip()
    reference_number = request.form.get("reference_number", "").strip()
    salary_info = request.form.get("salary_info", "").strip()

    try:
        result = finalize_job(client_slug, fields, job_specific_benefits,
                               employment_type, reference_number, salary_info)
    except MissingFieldsError as exc:
        missing_labels = ", ".join(exc.missing)
        error = f"Noch nicht vollstaendig, bitte ergaenzen: {missing_labels}"
        return render_template("review.html", **_review_context(
            client_slug, fields, job_specific_benefits, employment_type, reference_number,
            salary_info, raw_text=raw_text, error=error))
    except ClientConfigError as exc:
        return render_template("form.html", clients=list_client_slugs(), error=f"Kundenkonfiguration: {exc}")

    return render_template(
        "result.html",
        fields=result.fields,
        docx_url=url_for("download", output_dir=result.output_dir.name, client_slug=client_slug,
                          filename=result.docx_name),
        payload_url=url_for("download", output_dir=result.output_dir.name, client_slug=client_slug,
                             filename=result.payload_name),
    )


@app.route("/download/<client_slug>/<output_dir>/<filename>")
def download(client_slug: str, output_dir: str, filename: str):
    directory = resolve_output_dir(OUTPUT_BASE, client_slug, output_dir)
    return send_from_directory(directory, filename, as_attachment=True)


if __name__ == "__main__":
    # Debug-Modus (Werkzeug-Debugger) erlaubt Ausfuehrung beliebigen Codes im Browser -
    # standardmaessig aus, nur ueber die Umgebungsvariable bewusst fuer die eigene lokale
    # Entwicklung aktivierbar (siehe Docstring oben fuer den empfohlenen `flask --debug`-Weg).
    debug_mode = os.environ.get("RECRUITFLOW_DEBUG", "").lower() in ("1", "true")
    app.run(debug=debug_mode, port=5050)
