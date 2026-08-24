from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_public_tree_contains_no_generated_or_private_artifacts() -> None:
    forbidden_suffixes = {".so", ".dylib", ".dll", ".exe", ".jar", ".pdf", ".pth", ".pt"}
    for path in ROOT.rglob("*"):
        generated = {"__pycache__", ".pytest_cache"}.intersection(path.parts)
        if path.is_file() and not generated:
            assert path.suffix.lower() not in forbidden_suffixes, path


def test_readme_has_short_install_and_run_paths() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "pip install -e ." in readme
    assert "ksplay smoke" in readme
    assert "ksplay serve" in readme
    assert "setup.py build_ext --inplace" not in readme


def test_distribution_declares_all_license_texts() -> None:
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license-files = ["LICENSE", "NOTICE", "RLCard-MIT.md"]' in metadata
