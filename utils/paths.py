"""Pfad-Sicherheit fuer CLI-Eingaben (Client-/Job-Slugs)."""
import re
from pathlib import Path

_SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def safe_slug(value: str, field_name: str = "slug") -> str:
    """Gibt value zurueck, wenn es ein sicherer Datei-/Ordnername ist, sonst ValueError.

    Verhindert Path-Traversal (z.B. '../etc') bei per CLI uebergebenen
    Client- oder Job-Slugs, die spaeter in Dateipfade einfliessen.
    """
    if not value or not _SLUG_RE.match(value):
        raise ValueError(
            f"{field_name} darf nur Buchstaben, Ziffern, '_' und '-' enthalten, "
            f"erhalten: {value!r}"
        )
    return value


def resolve_output_dir(base_dir: Path, client_slug: str, job_slug: str) -> Path:
    """Baut den Output-Pfad und stellt sicher, dass er innerhalb von base_dir bleibt."""
    base_dir = base_dir.resolve()
    candidate = (base_dir / client_slug / job_slug).resolve()
    if not candidate.is_relative_to(base_dir):
        raise ValueError(f"Unsicherer Output-Pfad: {candidate} liegt ausserhalb von {base_dir}")
    return candidate
