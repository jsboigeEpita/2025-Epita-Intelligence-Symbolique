"""Smoke tests for the soutenance slide deck (Issue #406).

Validates:
- slides.md exists and has >= 25 slides
- build_deck.py produces valid HTML without error
- No plaintext dataset extracts in slides
- Build output is gitignored
- All assets under 100KB
"""
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SLIDES_MD = REPO_ROOT / "docs" / "soutenance" / "slides.md"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_deck.py"
GITIGNORE = REPO_ROOT / ".gitignore"
BUILD_OUTPUT_DIR = REPO_ROOT / "docs" / "soutenance" / "build"

SLIDE_SEPARATOR = re.compile(r"\n---\n")

SENSITIVE_FIELDS = ("source_name", "full_text", "raw_text")


class TestSlideSource:
    """Tests for docs/soutenance/slides.md."""

    def test_slides_md_exists(self):
        assert SLIDES_MD.is_file(), f"slides.md not found at {SLIDES_MD}"

    def test_minimum_25_slides(self):
        content = SLIDES_MD.read_text(encoding="utf-8")
        sections = SLIDE_SEPARATOR.split(content)
        non_empty = [s.strip() for s in sections if s.strip()]
        assert len(non_empty) >= 25, (
            f"Expected >= 25 slides, found {len(non_empty)}"
        )

    def test_has_frontmatter(self):
        content = SLIDES_MD.read_text(encoding="utf-8")
        assert content.startswith("---"), "slides.md must start with YAML frontmatter"
        parts = content.split("---", 2)
        assert len(parts) >= 3, "Frontmatter must be delimited by ---"
        fm = parts[1]
        assert "title:" in fm, "Frontmatter missing 'title'"
        assert "theme:" in fm, "Frontmatter missing 'theme'"

    def test_no_plaintext_extracts(self):
        content = SLIDES_MD.read_text(encoding="utf-8").lower()
        for field in SENSITIVE_FIELDS:
            assert field not in content, (
                f"Found sensitive field '{field}' in slides.md"
            )

    def test_opaque_ids_only(self):
        content = SLIDES_MD.read_text(encoding="utf-8")
        has_doc_ref = "doc_a" in content.lower() or "doc_A" in content
        if has_doc_ref:
            assert "source_name" not in content.lower()
            assert "extract_sources" not in content.lower()

    def test_covers_17_phases(self):
        content = SLIDES_MD.read_text(encoding="utf-8")
        assert "17" in content, "Slides should mention 17 phases"

    def test_covers_architecture_section(self):
        content = SLIDES_MD.read_text(encoding="utf-8").lower()
        assert "architecture" in content, "Slides should cover architecture"
        assert "multi-agent" in content, "Slides should mention multi-agents"

    def test_covers_scenarios(self):
        content = SLIDES_MD.read_text(encoding="utf-8").lower()
        assert "politique" in content or "politic" in content
        assert "scient" in content or "climat" in content

    def test_file_size_under_100kb(self):
        size = SLIDES_MD.stat().st_size
        assert size < 100 * 1024, f"slides.md is {size} bytes, exceeds 100KB"


class TestBuildScript:
    """Tests for scripts/build_deck.py."""

    def test_build_script_exists(self):
        assert BUILD_SCRIPT.is_file(), f"build_deck.py not found at {BUILD_SCRIPT}"

    def test_build_produces_html(self, tmp_path):
        sys.path.insert(0, str(BUILD_SCRIPT.parent.parent / "scripts"))
        from build_deck import build_deck

        output = tmp_path / "slides.html"
        result = build_deck(SLIDES_MD, output)
        assert result.is_file(), "Build did not produce output file"

        html = result.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html, "Output is not valid HTML"
        assert "reveal.js" in html, "Output does not reference reveal.js"
        assert "data-markdown" in html, "Output missing data-markdown sections"

    def test_build_output_sections_match_source(self, tmp_path):
        from build_deck import build_deck, parse_frontmatter

        output = tmp_path / "slides.html"
        build_deck(SLIDES_MD, output)
        html = output.read_text(encoding="utf-8")

        section_count = html.count("<section data-markdown>")
        md_content = SLIDES_MD.read_text(encoding="utf-8")
        _, body = parse_frontmatter(md_content)
        md_sections = [
            s.strip() for s in SLIDE_SEPARATOR.split(body) if s.strip()
        ]
        assert section_count == len(md_sections), (
            f"HTML has {section_count} sections but source has {len(md_sections)}"
        )

    def test_build_output_under_100kb(self, tmp_path):
        from build_deck import build_deck

        output = tmp_path / "slides.html"
        build_deck(SLIDES_MD, output)
        size = output.stat().st_size
        assert size < 100 * 1024, f"Built HTML is {size} bytes, exceeds 100KB"


class TestGitignore:
    """Ensure build artifacts are excluded from git."""

    def test_build_dir_gitignored(self):
        gitignore = GITIGNORE.read_text(encoding="utf-8")
        assert "docs/soutenance/build/" in gitignore or (
            "build/" in gitignore
        ), "docs/soutenance/build/ should be gitignored"
