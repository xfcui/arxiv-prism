"""Shared text processing: strip citations, convert links to markdown."""

import logging
import re

logger = logging.getLogger(__name__)


def strip_citations(text: str) -> str:
    """Remove citation markers like [1], [1, 2], superscript refs, and empty citation artifacts."""
    if not text or not text.strip():
        return text
    
    # Remove [...]. e.g. [1], [1, 2], [1-3]
    text = re.sub(r"\[\s*\d+(?:\s*[,\-]\s*\d+)*\s*\]", "", text)
    
    # Remove empty citation artifacts with surrounding spaces
    # Patterns: (–), (, ), (,), ( ), etc., including leading/trailing spaces
    text = re.sub(r"\s*\(\s*[–\-,;]*\s*\)\s*", " ", text)
    
    # Remove standalone dashes or commas that were part of citations
    # Match patterns like " – " or " , " when surrounded by spaces or punctuation
    text = re.sub(r"\s+[–\-]\s+(?=[.,;:\s]|$)", " ", text)
    text = re.sub(r"(?<=\s)[,;]\s+(?=[.,;:\s]|$)", " ", text)
    
    # Clean up multiple punctuation marks left behind
    text = re.sub(r"([.,;:])\s*[,;]\s*", r"\1 ", text)
    
    # Remove duplicate periods and fix punctuation spacing
    text = re.sub(r"\.{2,}", ".", text)  # Multiple periods -> single period
    text = re.sub(r"\.\s+\.", ".", text)  # Period space period -> single period
    
    # Collapse multiple spaces/newlines
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    
    # Clean up spaces before punctuation
    text = re.sub(r"\s+([.,;:)])", r"\1", text)
    
    return text.strip()


def link_to_markdown(href: str, link_text: str) -> str:
    """Format as markdown link [text](url)."""
    href = (href or "").strip()
    link_text = (link_text or href or "").strip()
    if not href or href.startswith("#"):
        return link_text
    return f"[{link_text}]({href})"
