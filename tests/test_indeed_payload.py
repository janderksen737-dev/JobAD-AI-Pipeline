from indeed_integration.indeed_client import build_indeed_payload

AGENCY = {
    "agency_name": "Sample Recruiting GmbH",
    "agency_email": "test@sample-recruiting.example",
    "agency_phone": "+49300000000",
    "agency_website": "www.sample-recruiting.example",
    "contact_person": "Test Person",
}

COMMON_KWARGS = dict(
    job_title="Testingenieur",
    employment_type="Vollzeit",
    location="Berlin",
    start_date="sofort",
    tasks=["Testaufgabe"],
    profile=["Testanforderung"],
    benefits=["Testvorteil"],
    agency=AGENCY,
)


def _company_name(payload):
    return payload["variables"]["jobPostings"][0]["metadata"]["jobSource"]["companyName"]


def test_company_name_reflects_client_description_not_a_fixed_string():
    payload_a = build_indeed_payload(client_description="Unternehmen für Flugzeugbauteile", **COMMON_KWARGS)
    payload_b = build_indeed_payload(
        client_description="international tätiges Unternehmen der Luft- und Raumfahrtbranche",
        **COMMON_KWARGS,
    )

    assert _company_name(payload_a) == "Unternehmen für Flugzeugbauteile"
    assert _company_name(payload_b) == "international tätiges Unternehmen der Luft- und Raumfahrtbranche"
    assert _company_name(payload_a) != _company_name(payload_b)
