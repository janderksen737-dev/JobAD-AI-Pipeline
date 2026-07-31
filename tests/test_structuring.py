from pathlib import Path

import pytest

from config.client_config import load_client_config
from engine.structuring import load_system_prompt, structure_freetext

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class _FakeToolUseBlock:
    def __init__(self, input_data: dict):
        self.type = "tool_use"
        self.input = input_data


class _FakeResponse:
    def __init__(self, input_data: dict):
        self.content = [_FakeToolUseBlock(input_data)]


class _FakeMessages:
    def __init__(self, input_data: dict):
        self._input_data = input_data
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        return _FakeResponse(self._input_data)


class _FakeAnthropicClient:
    def __init__(self, input_data: dict):
        self.messages = _FakeMessages(input_data)


@pytest.fixture
def sample_client():
    return load_client_config("sample_client", clients_dir=FIXTURES_DIR)


def test_load_system_prompt_extracts_prompt():
    prompt = load_system_prompt()
    assert "Strukturierungs-Assistent" in prompt
    assert "```" not in prompt


def test_structure_freetext_complete_input(sample_client):
    canned_response = {
        "fields": {
            "job_title": "Systemingenieur Luft- und Raumfahrt",
            "client_description": "international tätiges Unternehmen der Luft- und Raumfahrtbranche",
            "location": "München",
            "start_date": "sofort",
            "employment_type": "Unbefristet mit Übernahmeoption",
            "tasks": ["Systemtechnische Entwicklung im internationalen Projektumfeld"],
            "profile": ["CATIA-Kenntnisse", "Sehr gute Englischkenntnisse"],
            "benefits": ["Option auf Übernahme"],
            "reference_number": None,
            "salary_info": None,
        },
        "missing_fields": [],
    }
    fake_client = _FakeAnthropicClient(canned_response)

    result = structure_freetext(
        "brauchen systems engineer für kunden aus luftfahrt, münchen, muss catia können ...",
        sample_client,
        client=fake_client,
    )

    assert result.fields.job_title == "Systemingenieur Luft- und Raumfahrt"
    assert result.missing_fields == []
    # Kontext des Kunden muss im System-Prompt gelandet sein
    assert sample_client.industry_context in fake_client.messages.last_call_kwargs["system"]


def test_structure_freetext_reports_missing_fields(sample_client):
    canned_response = {
        "fields": {
            "job_title": "Qualitätsingenieur",
            "client_description": "Unternehmen für Flugzeugbauteile",
            "location": None,
            "start_date": "zeitnah",
            "employment_type": None,
            "tasks": ["Qualitätssicherung im Bereich Flugzeugbauteile"],
            "profile": ["SAP-Kenntnisse von Vorteil"],
            "benefits": [],
            "reference_number": None,
            "salary_info": None,
        },
        "missing_fields": ["location", "employment_type"],
    }
    fake_client = _FakeAnthropicClient(canned_response)

    result = structure_freetext(
        "qualitätsingenieur gesucht, kunde macht bauteile für flugzeuge, sap wär gut...",
        sample_client,
        client=fake_client,
    )

    assert result.missing_fields == ["location", "employment_type"]
    assert result.fields.location is None
