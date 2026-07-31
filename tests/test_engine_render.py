from pathlib import Path

import pytest

from config.client_config import load_client_config
from engine.engine import render_posting

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def sample_client():
    return load_client_config("sample_client", clients_dir=FIXTURES_DIR)


def test_render_posting_writes_docx(sample_client, tmp_path):
    output_path = tmp_path / "output.docx"
    result = render_posting(
        agency=sample_client.agency.model_dump(),
        standard_benefits=sample_client.standard_benefits,
        template_path=sample_client.resolved_template_path(),
        logo_path=sample_client.resolved_logo_path(),
        client_specific_benefits=["Job-spezifischer Vorteil"],
        job_title="Testingenieur",
        client_description="Testunternehmen",
        location="Berlin",
        start_date="sofort",
        tasks=["Testaufgabe"],
        profile=["Testanforderung"],
        output_path=str(output_path),
    )
    assert Path(result) == output_path
    assert output_path.is_file()


def test_render_posting_raises_on_missing_required_field(sample_client, tmp_path):
    with pytest.raises(ValueError):
        render_posting(
            agency=sample_client.agency.model_dump(),
            standard_benefits=sample_client.standard_benefits,
            template_path=sample_client.resolved_template_path(),
            logo_path=sample_client.resolved_logo_path(),
            client_specific_benefits=[],
            job_title="Testingenieur",
            client_description="Testunternehmen",
            location="Berlin",
            # start_date fehlt absichtlich
            tasks=["Testaufgabe"],
            profile=["Testanforderung"],
            output_path=str(tmp_path / "output.docx"),
        )
