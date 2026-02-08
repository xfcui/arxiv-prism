"""Markdown formatter for article output."""

from arxiv_prism.models import Article, Section
from arxiv_prism.formatters.base import BaseFormatter


def _section_to_md(section: Section, heading_base: int) -> str:
    """Render a section and its nested sections to Markdown."""
    lines = []
    level = heading_base + section.level - 1
    prefix = "#" * min(level, 6)
    if section.title:
        lines.append(f"{prefix} {section.title}")
        lines.append("")
    if section.content.strip():
        lines.append(section.content.strip())
        lines.append("")
    for sub in section.sections:
        lines.append(_section_to_md(sub, heading_base))
    return "\n".join(lines)


def _table_to_md(data: list[list[str]]) -> str:
    """Convert table data to Markdown table."""
    if not data:
        return ""
    lines = []
    header = data[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for row in data[1:]:
        # Pad row to header length
        row = list(row) + [""] * (len(header) - len(row))
        row = row[: len(header)]
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


class MarkdownFormatter(BaseFormatter):
    """Format Article as Markdown."""

    def format(self, article: Article) -> str:
        """Render article as Markdown with headings, figures, tables."""
        lines = []
        lines.append(f"# {article.title}")
        lines.append("")
        if article.doi:
            lines.append(f"DOI: {article.doi}")
            lines.append("")
        if article.abstract:
            lines.append("## Abstract")
            lines.append("")
            lines.append(article.abstract.strip())
            lines.append("")
        for section in article.sections:
            lines.append(_section_to_md(section, heading_base=2))
        if article.figures:
            lines.append("---")
            lines.append("")
            for fig in article.figures:
                lines.append(f"**{fig.label or fig.id}**: {fig.caption}")
                lines.append("")
        if article.tables:
            lines.append("---")
            lines.append("")
            for tbl in article.tables:
                lines.append(f"**{tbl.label or tbl.id}**: {tbl.caption}")
                lines.append("")
                lines.append(_table_to_md(tbl.data))
                lines.append("")
        if article.supplementary:
            lines.append("## Supplementary Materials")
            lines.append("")
            for supp in article.supplementary:
                lines.append(f"- **{supp.label}**: {supp.description}")
            lines.append("")
        return "\n".join(lines).strip() + "\n"
