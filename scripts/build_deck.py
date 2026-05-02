#!/usr/bin/env python3
"""Build reveal.js HTML slide deck from markdown source.

Usage:
    python scripts/build_deck.py [--source docs/soutenance/slides.md] [--output docs/soutenance/build/slides.html]
"""
import argparse
import pathlib
import re

REVEAL_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="{reveal_url}/dist/reveal.css">
    <link rel="stylesheet" href="{reveal_url}/dist/theme/{theme}.css">
    <style>
        .reveal h1, .reveal h2 {{ font-weight: bold; }}
        .reveal table {{ font-size: 0.7em; border-collapse: collapse; margin: 10px auto; }}
        .reveal th {{ background: #2c3e50; color: white; padding: 6px 12px; }}
        .reveal td {{ border: 1px solid #ddd; padding: 4px 10px; }}
        .reveal code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 0.85em; }}
        .reveal pre code {{ display: block; padding: 12px; overflow-x: auto; }}
        .reveal blockquote {{ border-left: 4px solid #2c3e50; padding-left: 12px; font-style: italic; }}
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
{slides_html}
        </div>
    </div>
    <script src="{reveal_url}/dist/reveal.js"></script>
    <script>
        Reveal.initialize({{
            hash: true,
            slideNumber: true,
            transition: 'slide',
            width: 1200,
            height: 800
        }});
    </script>
</body>
</html>"""

SLIDE_SEPARATOR = re.compile(r"\n---\n")


def markdown_to_slides(md_content: str) -> str:
    """Convert markdown with --- separators to reveal.js section tags."""
    sections = SLIDE_SEPARATOR.split(md_content)
    html_sections = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        html_sections.append(f"            <section data-markdown>\n                <textarea data-template>\n{section}\n                </textarea>\n            </section>")
    return "\n".join(html_sections)


def parse_frontmatter(md_content: str):
    """Extract YAML frontmatter from markdown."""
    if md_content.startswith("---"):
        parts = md_content.split("---", 2)
        if len(parts) >= 3:
            fm = {}
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    fm[key.strip()] = val.strip().strip('"').strip("'")
            return fm, parts[2]
    return {}, md_content


def build_deck(source: pathlib.Path, output: pathlib.Path) -> pathlib.Path:
    """Build reveal.js HTML deck from markdown source."""
    md_content = source.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(md_content)

    title = fm.get("title", "Presentation")
    reveal_url = fm.get("revealjs-url", "https://cdn.jsdelivr.net/npm/reveal.js@5")
    theme = fm.get("theme", "white")

    slides_html = markdown_to_slides(body)

    html = REVEAL_TEMPLATE.format(
        title=title,
        reveal_url=reveal_url,
        theme=theme,
        slides_html=slides_html,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description="Build reveal.js slide deck")
    parser.add_argument("--source", type=pathlib.Path, default=pathlib.Path("docs/soutenance/slides.md"))
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("docs/soutenance/build/slides.html"))
    args = parser.parse_args()
    result = build_deck(args.source, args.output)
    print(f"Built: {result}")


if __name__ == "__main__":
    main()
