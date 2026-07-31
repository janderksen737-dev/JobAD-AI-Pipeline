import pytest

from utils.paths import resolve_output_dir, safe_slug


def test_safe_slug_accepts_valid_values():
    assert safe_slug("talentbridge-demo") == "talentbridge-demo"
    assert safe_slug("job_slug_123") == "job_slug_123"


def test_safe_slug_rejects_path_traversal():
    with pytest.raises(ValueError):
        safe_slug("../etc")


def test_safe_slug_rejects_empty():
    with pytest.raises(ValueError):
        safe_slug("")


def test_resolve_output_dir_stays_inside_base(tmp_path):
    result = resolve_output_dir(tmp_path, "client_a", "job_1")
    assert result.is_relative_to(tmp_path.resolve())


def test_resolve_output_dir_rejects_traversal(tmp_path):
    with pytest.raises(ValueError):
        resolve_output_dir(tmp_path, "..", "job_1")
