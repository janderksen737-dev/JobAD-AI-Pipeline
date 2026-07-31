"""
Simuliert die Indeed Job Sync API lokal, um die Integration zu testen,
ohne dass ein echter Indeed-Partnerzugang nötig ist.

Baut den echten GraphQL-Payload nach Indeeds offiziellem Schema
(jobsIngest.createSourcedJobPostings) aus unseren Engine-Daten und
schickt ihn an einen lokalen Mock-Endpunkt, der wie Indeed antwortet.
"""
import json
import logging
import os
import sys
import threading
import uuid
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------- 1. Mock-Server (simuliert Indeeds echtes Antwortverhalten) ----------

class MockIndeedHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # ruhig halten, keine Konsolen-Flut

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        variables = body.get("variables", {})
        job = variables["jobPostings"][0]
        errors = []

        # Validierung wie bei Indeed: Pflichtfelder prüfen
        if not job["body"].get("title"):
            errors.append("body.title is required")
        if not job["body"].get("description"):
            errors.append("body.description is required")
        if not job["metadata"]["jobSource"].get("sourceName"):
            errors.append("metadata.jobSource.sourceName is required")
        if not job["metadata"].get("jobPostingId"):
            errors.append("metadata.jobPostingId is required")
        if not job["metadata"]["contacts"][0]["contactInfo"].get("contactEmail"):
            errors.append("metadata.contacts.contactInfo.contactEmail is required")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        if errors:
            self.wfile.write(json.dumps({"errors": [{"message": e} for e in errors]}).encode())
            return

        sourced_id = str(uuid.uuid4())
        response = {
            "data": {
                "jobsIngest": {
                    "createSourcedJobPostings": {
                        "results": [
                            {"jobPosting": {"sourcedPostingId": sourced_id,
                                             "employerJobId": f"mock-{sourced_id[:8]}"}}
                        ]
                    }
                }
            }
        }
        self.wfile.write(json.dumps(response).encode())


def start_mock_server():
    server = HTTPServer(("localhost", 8891), MockIndeedHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


# ---------- 2. Payload-Builder: unsere Engine-Daten -> Indeed-Schema ----------

def build_indeed_payload(job_title, employment_type, location, start_date,
                          tasks, profile, benefits, agency, client_description,
                          job_posting_id=None):
    """
    Baut den GraphQL-Request exakt nach Indeeds createSourcedJobPostings-Schema
    (siehe docs.indeed.com/job-sync-api/job-sync-api-guide).

    client_description: die anonymisierte Branchenbeschreibung des Endkunden
    (von der KI-Strukturierung erzeugt, siehe engine/structuring_prompt.md,
    Regel 3: "Kundennamen werden nie übernommen"). Das ist NICHT der echte
    Firmenname des Endkunden, sondern pro Job unterschiedlich, je nach
    Branche/Kontext (z.B. "Unternehmen für Flugzeugbauteile" vs. "international
    tätiges Unternehmen der Luft- und Raumfahrtbranche") — anders als vorher,
    wo hier fuer jeden Job derselbe fest einprogrammierte String stand.
    """
    description_html = (
        f"<h2>Ihre Aufgaben</h2><ul>{''.join(f'<li>{t}</li>' for t in tasks)}</ul>"
        f"<h2>Ihr Profil</h2><ul>{''.join(f'<li>{p}</li>' for p in profile)}</ul>"
        f"<h2>Beschäftigungsart</h2><p>{employment_type}, Start: {start_date}</p>"
    )

    job_posting_id = job_posting_id or f"talentbridge-{uuid.uuid4().hex[:10]}"

    query = """
    mutation CreateJobPosting($jobPostings: [CreateSourcedJobPostingInput!]!) {
      jobsIngest {
        createSourcedJobPostings(input: { jobPostings: $jobPostings }) {
          results { jobPosting { sourcedPostingId employerJobId } }
        }
      }
    }
    """

    variables = {
        "jobPostings": [
            {
                "body": {
                    "title": job_title,
                    "description": description_html,
                    "location": {"country": "DE", "cityRegionPostal": location},
                    "benefits": benefits,
                },
                "metadata": {
                    "jobSource": {
                        "companyName": client_description,  # anonymisiert, pro Job unterschiedlich
                        "sourceName": agency["agency_name"],
                        "sourceType": "Employer",
                    },
                    "jobPostingId": job_posting_id,
                    "datePublished": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "url": f"{agency['agency_website']}/jobs/{job_posting_id}",
                    "contacts": [{
                        "contactType": ["contact"],
                        "contactInfo": {
                            "contactEmail": agency["agency_email"],
                            "contactPhone": agency["agency_phone"].replace(" ", ""),
                            "contactName": agency["contact_person"],
                        },
                    }],
                    "trackingUrl": f"https://{agency['agency_website']}",
                },
            }
        ]
    }

    return {"query": query, "variables": variables}


# ---------- 3. Testlauf ----------

if __name__ == "__main__":
    sys.path.insert(0, _REPO_ROOT)
    from utils.logging_setup import setup_logging

    setup_logging()
    start_mock_server()

    agency = {
        "agency_name": "TalentBridge Personalvermittlung GmbH",
        "agency_email": "kontakt@talentbridge-beispiel.de",
        "agency_phone": "+49891234567",
        "agency_website": "www.talentbridge-beispiel.de",
        "contact_person": "Max Mustermann",
    }

    payload = build_indeed_payload(
        job_title="Avionik-Systemtestingenieur (m/w/d) in Vollzeit",
        employment_type="Vollzeit",
        location="Hamburg",
        start_date="August",
        client_description="Unternehmen im Bereich Avioniksysteme",
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
        benefits=[
            "18-monatiger Vertrag mit klarer Übernahmeoption",
            "Persönliche und individuelle Betreuung durch unser erfahrenes Berater-Team",
            "Langfristige Perspektive mit Option auf Übernahme beim Kundenunternehmen",
            "Zugang zu einem breiten Netzwerk an Unternehmen der Luft- und Raumfahrtbranche",
        ],
        agency=agency,
    )

    logger.info("=== Gesendeter Payload (identisch zum echten Indeed-Format) ===")
    logger.info(json.dumps(payload["variables"], indent=2, ensure_ascii=False))

    resp = requests.post("http://localhost:8891/graphql", json=payload)
    logger.info("=== Antwort vom Mock-Endpunkt (simuliert Indeeds echtes Antwortformat) ===")
    logger.info(json.dumps(resp.json(), indent=2, ensure_ascii=False))
