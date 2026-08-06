import xml.etree.ElementTree as ET

from stepstone_integration.stepstone_client import build_stepstone_payload

AGENCY = {
    "agency_name": "Sample Recruiting GmbH",
    "agency_email": "test@sample-recruiting.example",
    "agency_phone": "+49300000000",
    "agency_website": "www.sample-recruiting.example",
    "contact_person": "Test Person",
}

COMMON_KWARGS = dict(
    job_title="Testingenieur",
    location="Berlin",
    tasks=["Testaufgabe"],
    profile=["Testanforderung"],
    benefits=["Testvorteil"],
    agency=AGENCY,
    sender_id="TEST-SENDER-ID",
    organisation_id="TEST-ORG-ID",
)


def _company_name(xml_payload: str) -> str:
    root = ET.fromstring(xml_payload)
    return root.find("joblisting/companydetails/companyname").text


def test_well_formed_xml():
    xml_payload = build_stepstone_payload(client_description="Unternehmen für Flugzeugbauteile", **COMMON_KWARGS)
    root = ET.fromstring(xml_payload)  # raises ET.ParseError if malformed
    assert root.tag == "jobfeed"


def test_required_attributes_present():
    xml_payload = build_stepstone_payload(client_description="Unternehmen für Flugzeugbauteile", **COMMON_KWARGS)
    root = ET.fromstring(xml_payload)
    joblisting = root.find("joblisting")
    assert joblisting.get("reference_id")
    assert joblisting.get("sender_id") == "TEST-SENDER-ID"
    assert joblisting.get("organisation_id") == "TEST-ORG-ID"
    assert joblisting.get("action") == "INSERT"


def test_company_name_reflects_client_description_not_a_fixed_string():
    payload_a = build_stepstone_payload(client_description="Unternehmen für Flugzeugbauteile", **COMMON_KWARGS)
    payload_b = build_stepstone_payload(
        client_description="international tätiges Unternehmen der Luft- und Raumfahrtbranche",
        **COMMON_KWARGS,
    )

    assert _company_name(payload_a) == "Unternehmen für Flugzeugbauteile"
    assert _company_name(payload_b) == "international tätiges Unternehmen der Luft- und Raumfahrtbranche"
    assert _company_name(payload_a) != _company_name(payload_b)
