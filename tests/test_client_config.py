from pathlib import Path

import pytest

from config.client_config import ClientConfigError, load_client_config

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_load_client_config_success():
    config = load_client_config("sample_client", clients_dir=FIXTURES_DIR)
    assert config.agency.agency_name == "Sample Recruiting GmbH"
    assert config.standard_benefits == ["Testvorteil A", "Testvorteil B"]
    assert config.industry_context == "Test-Branche fuer automatisierte Tests."


def test_load_client_config_missing_client():
    with pytest.raises(ClientConfigError):
        load_client_config("does_not_exist", clients_dir=FIXTURES_DIR)


def test_load_client_config_malformed_yaml(tmp_path):
    client_dir = tmp_path / "broken_client"
    client_dir.mkdir()
    (client_dir / "config.yaml").write_text("agency: [this is not: valid: yaml", encoding="utf-8")

    with pytest.raises(ClientConfigError):
        load_client_config("broken_client", clients_dir=tmp_path)


def test_load_client_config_incomplete_fields(tmp_path):
    client_dir = tmp_path / "incomplete_client"
    client_dir.mkdir()
    (client_dir / "config.yaml").write_text("slug: incomplete_client\n", encoding="utf-8")

    with pytest.raises(ClientConfigError):
        load_client_config("incomplete_client", clients_dir=tmp_path)
