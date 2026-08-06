"""
Simuliert StepStones JobFeed-API lokal, um die Integration zu testen,
ohne dass ein echter StepStone-Kundenvertrag noetig ist.

Baut das echte XML-Format nach StepStones JobFeed-Schema (siehe
api.stepstone.com/stepstone-xml-guide) aus unseren Engine-Daten und
schickt es an einen lokalen Mock-Endpunkt, der wie StepStone antwortet.

Wichtig: sender_id/organisation_id sind die echten, pro Kunde von StepStone
vergebenen Zugangsdaten (siehe research/notes/feasibility_stepstone.md) -
die existieren noch nicht, solange kein echter Kunde einen StepStone-Vertrag
hat. Dieses Modul beweist nur, dass die Payload-Erzeugung korrekt
funktioniert; es ist bewusst NICHT an run_pipeline.py angebunden.
"""
import logging
import os
import sys
import threading
import uuid
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------- 1. Mock-Server (simuliert StepStones echtes Antwortverhalten) ----------

class MockStepStoneHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # ruhig halten, keine Konsolen-Flut

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        errors = []

        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            self._respond(400, [f"Invalid XML: {exc}"])
            return

        joblisting = root.find("joblisting")
        if joblisting is None:
            self._respond(400, ["joblisting element is required"])
            return

        # Validierung wie bei StepStone: Pflichtfelder pruefen
        for attr in ("reference_id", "sender_id", "organisation_id", "action"):
            if not joblisting.get(attr):
                errors.append(f"joblisting@{attr} is required")

        jobdetails = joblisting.find("jobdetails")
        if jobdetails is None:
            errors.append("jobdetails is required")
        else:
            if not (jobdetails.findtext("jobtitle") or "").strip():
                errors.append("jobdetails/jobtitle is required")
            if not (jobdetails.findtext("tasks") or "").strip():
                errors.append("jobdetails/tasks is required")

        companydetails = joblisting.find("companydetails")
        if companydetails is None or not (companydetails.findtext("companyname") or "").strip():
            errors.append("companydetails/companyname is required")

        if errors:
            self._respond(400, errors)
            return

        self._respond(200, [])

    def _respond(self, status: int, errors: list[str]) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/xml")
        self.end_headers()

        if errors:
            error_els = "".join(f"<error>{e}</error>" for e in errors)
            self.wfile.write(f"<response><errors>{error_els}</errors></response>".encode())
            return

        job_id = str(uuid.uuid4())
        self.wfile.write(
            f"<response><status>accepted</status><job_id>{job_id}</job_id></response>".encode()
        )


def start_mock_server():
    server = HTTPServer(("localhost", 8892), MockStepStoneHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


# ---------- 2. Payload-Builder: unsere Engine-Daten -> StepStone-XML-Schema ----------

def build_stepstone_payload(job_title, client_description, location, tasks, profile,
                             benefits, agency, sender_id, organisation_id, reference_id=None):
    """
    Baut das JobFeed-XML exakt nach StepStones Schema
    (siehe api.stepstone.com/stepstone-xml-guide, api.stepstone.com/full-xml-example).

    sender_id/organisation_id: echte, von StepStone pro Kunde vergebene
    Zugangsdaten (siehe research/notes/feasibility_stepstone.md) - es gibt
    keinen einzelnen Anbieter-Key wie bei Indeed. Muessen explizit uebergeben
    werden, damit hier nichts Reales vorgetaeuscht wird, solange kein
    Kundenvertrag existiert.

    client_description: dieselbe anonymisierte Branchenbeschreibung wie im
    Indeed-Payload (siehe indeed_integration/indeed_client.py) - nie der
    echte Firmenname des Endkunden.

    Gibt das fertige XML-Dokument als String zurueck (UTF-8, siehe
    ET.tostring mit xml_declaration=True).
    """
    reference_id = reference_id or f"talentbridge-{uuid.uuid4().hex[:10]}"
    first_name, _, last_name = agency["contact_person"].partition(" ")

    jobfeed = ET.Element("jobfeed")
    joblisting = ET.SubElement(jobfeed, "joblisting", {
        "reference_id": reference_id,
        "sender_id": sender_id,
        "organisation_id": organisation_id,
        "action": "INSERT",
    })

    jobdetails = ET.SubElement(joblisting, "jobdetails")
    ET.SubElement(jobdetails, "language").text = "de"
    ET.SubElement(jobdetails, "jobtitle").text = job_title
    ET.SubElement(jobdetails, "introduction").text = client_description
    ET.SubElement(jobdetails, "tasks").text = "\n".join(f"- {t}" for t in tasks)
    ET.SubElement(jobdetails, "profile").text = "\n".join(f"- {p}" for p in profile)
    ET.SubElement(jobdetails, "offer").text = "\n".join(f"- {b}" for b in benefits)

    joblocations = ET.SubElement(jobdetails, "joblocations")
    location_el = ET.SubElement(joblocations, "location")
    ET.SubElement(location_el, "countrycode").text = "DE"
    ET.SubElement(location_el, "city").text = location

    contactinfo = ET.SubElement(jobdetails, "contactinfo")
    ET.SubElement(contactinfo, "email").text = agency["agency_email"]
    ET.SubElement(contactinfo, "phone").text = agency["agency_phone"]

    companydetails = ET.SubElement(joblisting, "companydetails")
    ET.SubElement(companydetails, "companyname").text = client_description
    recruiter = ET.SubElement(companydetails, "recruiter")
    ET.SubElement(recruiter, "firstname").text = first_name
    ET.SubElement(recruiter, "lastname").text = last_name or first_name
    ET.SubElement(recruiter, "email").text = agency["agency_email"]
    ET.SubElement(recruiter, "phone").text = agency["agency_phone"]

    return ET.tostring(jobfeed, encoding="unicode", xml_declaration=False)


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

    xml_payload = build_stepstone_payload(
        job_title="Avionik-Systemtestingenieur (m/w/d) in Vollzeit",
        client_description="Unternehmen im Bereich Avioniksysteme",
        location="Hamburg",
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
        ],
        agency=agency,
        # Platzhalter: echte Werte gibt es erst mit einem echten StepStone-Kundenvertrag
        sender_id="TEST-SENDER-ID",
        organisation_id="TEST-ORG-ID",
    )

    logger.info("=== Gesendetes XML (identisch zum echten StepStone-Format) ===")
    logger.info(xml_payload)

    resp = requests.post(
        "http://localhost:8892/jobfeed",
        data=xml_payload.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    logger.info("=== Antwort vom Mock-Endpunkt (simuliert StepStones Antwortformat) ===")
    logger.info(resp.text)
