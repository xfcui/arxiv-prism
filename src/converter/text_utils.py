"""Shared text processing: strip citations, convert links to markdown."""

import logging
import re

logger = logging.getLogger(__name__)


def strip_citations(text: str) -> str:
    """Remove citation markers like [1], [1, 2], superscript refs."""
    if not text or not text.strip():
        return text
    # Remove [...]. e.g. [1], [1, 2], [1-3]
    text = re.sub(r"\[\s*\d+(?:\s*[,\-]\s*\d+)*\s*\]", "", text)
    # Collapse multiple spaces/newlines
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def link_to_markdown(href: str, link_text: str) -> str:
    """Format as markdown link [text](url)."""
    href = (href or "").strip()
    link_text = (link_text or href or "").strip()
    if not href or href.startswith("#"):
        return link_text
    return f"[{link_text}]({href})"
