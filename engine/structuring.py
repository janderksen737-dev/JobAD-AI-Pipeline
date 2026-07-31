"""
KI-Strukturierungsschritt: wandelt Freitext (Kundennotiz oder Anforderungsdokument)
in das Feld-Schema um, das engine.render_posting() erwartet.

Der eigentliche Prompt lebt in engine/structuring_prompt.md (single source of
truth, siehe load_system_prompt) - hier steht nur die Anbindung an die
Anthropic API mit erzwungener, schema-validierter Ausgabe (Tool-Use), damit
"erfinde niemals fehlende Angaben" tatsaechlich durch Code garantiert wird
und nicht nur durch den Prompt-Text erhofft.
"""
import re
from pathlib import Path

import anthropic
from pydantic import BaseModel, ValidationError

_REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_MD_PATH = _REPO_ROOT / "engine" / "structuring_prompt.md"

_SYSTEM_PROMPT_RE = re.compile(r"## System-Prompt\s*\n\s*```\n(.*?)\n```", re.DOTALL)


class StructuringError(Exception):
    """Wird bei Fehlern der KI-Strukturierung ausgeloest (nie stillschweigend erfinden)."""


class RawStructuredFields(BaseModel):
    job_title: str | None = None
    client_description: str | None = None
    location: str | None = None
    start_date: str | None = None
    employment_type: str | None = None
    tasks: list[str] = []
    profile: list[str] = []
    benefits: list[str] = []
    reference_number: str | None = None
    salary_info: str | None = None


class StructuringResponse(BaseModel):
    fields: RawStructuredFields
    missing_fields: list[str] = []


def load_system_prompt(path: Path = PROMPT_MD_PATH) -> str:
    """Extrahiert den eingebetteten System-Prompt aus structuring_prompt.md."""
    text = path.read_text(encoding="utf-8")
    match = _SYSTEM_PROMPT_RE.search(text)
    if not match:
        raise StructuringError(
            f"Konnte den System-Prompt nicht aus {path} extrahieren "
            f"(erwarte '## System-Prompt' gefolgt von einem ```-Codeblock)."
        )
    return match.group(1).strip()


def structure_freetext(
    raw_text: str,
    client_config,
    client: "anthropic.Anthropic | None" = None,
    model: str = "claude-sonnet-5",
) -> StructuringResponse:
    """Strukturiert Freitext via Anthropic API mit erzwungener Schema-Ausgabe.

    client ist injizierbar, damit Tests nie die echte API aufrufen.
    """
    system_prompt = load_system_prompt()
    if client_config.industry_context:
        system_prompt = (
            f"{system_prompt}\n\n"
            f"Zusaetzlicher Kontext zu dieser Personalvermittlung:\n"
            f"{client_config.industry_context}"
        )

    anthropic_client = client or anthropic.Anthropic()

    tool = {
        "name": "submit_structured_fields",
        "description": (
            "Uebermittelt die strukturierten Job-Felder sowie die Liste "
            "fehlender Pflichtangaben (falls vorhanden)."
        ),
        "input_schema": StructuringResponse.model_json_schema(),
    }

    try:
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_structured_fields"},
            messages=[{"role": "user", "content": raw_text}],
        )
    except anthropic.APIError as exc:
        raise StructuringError(f"Anthropic-API-Fehler bei der Strukturierung: {exc}") from exc

    tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
    if not tool_use_blocks:
        raise StructuringError("Keine strukturierte Antwort vom Modell erhalten (kein tool_use-Block).")

    try:
        return StructuringResponse.model_validate(tool_use_blocks[0].input)
    except ValidationError as exc:
        raise StructuringError(
            f"Antwort des Modells entspricht nicht dem erwarteten Schema: {exc}"
        ) from exc
