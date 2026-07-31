"""Laedt und validiert die Pro-Kunden-Konfiguration aus clients/<slug>/config.yaml."""
from pathlib import Path

import yaml
from pydantic import BaseModel

from utils.paths import safe_slug

REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENTS_DIR = REPO_ROOT / "clients"


class ClientConfigError(Exception):
    """Wird bei fehlender oder fehlerhafter Kundenkonfiguration ausgeloest."""


class AgencyIdentity(BaseModel):
    agency_name: str
    agency_street: str
    agency_zip_city: str
    agency_phone: str
    agency_email: str
    agency_website: str
    contact_person: str


class TemplateConfig(BaseModel):
    docx_path: str
    logo_path: str


class ClientConfig(BaseModel):
    slug: str
    agency: AgencyIdentity
    template: TemplateConfig
    standard_benefits: list[str] = []
    industry_context: str = ""

    def resolved_template_path(self, repo_root: Path = REPO_ROOT) -> Path:
        return (repo_root / self.template.docx_path).resolve()

    def resolved_logo_path(self, repo_root: Path = REPO_ROOT) -> Path:
        return (repo_root / self.template.logo_path).resolve()


def load_client_config(slug: str, clients_dir: Path = CLIENTS_DIR) -> ClientConfig:
    """Laedt clients/<slug>/config.yaml. Wirft ClientConfigError mit klarer Meldung bei Problemen."""
    safe_slug(slug, field_name="client")
    config_path = clients_dir / slug / "config.yaml"

    if not config_path.is_file():
        raise ClientConfigError(
            f"Keine Konfiguration gefunden fuer Kunde '{slug}' (erwartet: {config_path}). "
            f"Siehe clients/README.md, um einen neuen Kunden anzulegen."
        )

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ClientConfigError(f"config.yaml fuer '{slug}' ist kein gueltiges YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ClientConfigError(f"config.yaml fuer '{slug}' muss ein YAML-Objekt sein, erhalten: {type(raw)}")

    try:
        return ClientConfig.model_validate(raw)
    except Exception as exc:  # pydantic.ValidationError
        raise ClientConfigError(f"config.yaml fuer '{slug}' ist unvollstaendig/fehlerhaft: {exc}") from exc
