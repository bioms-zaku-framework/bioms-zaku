"""EN: one version, declared once. `__version__` in `src/bioms_zaku/__init__.py` is the single source (PEP 440,
SemVer 2.0.0); pyproject reads it, and CITATION.cff and the docs page must agree with it. Without this test the
declarations drift: they did, between 2026-09-10 and 2026-09-17."""
import importlib.metadata as md
import re
from pathlib import Path

import pytest
import yaml

from bioms_zaku import __version__

ROOT = Path(__file__).resolve().parents[1]
# EN: canonical public version (PEP 440, normalized form): no hyphen, no underscore, no uppercase.
CANONICAL = re.compile(r"^\d+(\.\d+)*((a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?$")


def test_version_is_canonical_pep440():
    assert CANONICAL.match(__version__), f"{__version__!r} is not a canonical PEP 440 version (write 1.0.0rc1, not 1.0.0-rc1)"


def test_pyproject_reads_the_single_source():
    txt = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in txt, "pyproject must take the version from the package, never declare its own"
    assert "[tool.hatch.version]" in txt and 'path = "src/bioms_zaku/__init__.py"' in txt


def test_citation_file_agrees():
    cff = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    assert str(cff["version"]) == __version__, "CITATION.cff is what a reader cites: it must name the version it ships with"


def test_docs_page_agrees():
    html = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    for place, needle in (("badge", f'<span class="badge">v{__version__}</span>'),
                          ("citation example", f"Version {__version__}."),
                          ("footer", f"BioMS Zaku v{__version__} ·")):
        assert needle in html, f"docs/index.html: the {place} does not name version {__version__}"


def test_the_contract_carries_the_package_version():
    """EN: ONE version line. Until 2026-09-19 the contract was versioned apart from the package: its title said v0.5.2,
    its change log numbered a v1.1.0-rc1 that ran AHEAD of the package's 1.0.0rc1, and the documentation page printed
    both at once. A reviewer holding a manifest could not tell which contract produced that number. The contract now
    carries the package version, and this test is what stops the two lines from parting again."""
    head = (ROOT / "CONTRACTS.md").read_text(encoding="utf-8").splitlines()[0]
    assert f"contracts of v{__version__}" in head, f"the title says {head!r} and does not carry the package version {__version__}"


def test_installed_metadata_agrees():
    """EN: proves the build really read the single source (and normalized to the same string)."""
    try:
        installed = md.version("bioms-zaku")
    except md.PackageNotFoundError:                      # EN: source tree only, nothing installed — nothing to compare
        pytest.skip("bioms-zaku is not installed in this environment")
    assert installed == __version__, (
        f"the installed distribution says {installed}, the source says {__version__}: either the declarations drifted "
        "or the installed copy is stale (reinstall it: pip install --force-reinstall dist/*.whl)")
