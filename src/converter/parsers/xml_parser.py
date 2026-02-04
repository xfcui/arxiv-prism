"""XML parser for PubMed Central JATS format."""

import logging
import re
from xml.etree import ElementTree as ET

from converter.models import (
    Article,
    Figure,
    Section,
    Table,
)
from converter.models import Supplementary  # noqa: F401 - used in return type
from converter.parsers.base import BaseParser
from converter.text_utils import strip_citations
from converter.math_utils import mathml_element_to_latex

logger = logging.getLogger(__name__)

NS = {"mml": "http://www.w3.org/1998/Math/MathML", "xlink": "http://www.w3.org/1999/xlink"}


def _text(el: ET.Element | None) -> str:
    """Recursive text of element and children."""
    if el is None:
        return ""
    return " ".join(el.itertext()) if el.itertext else ""


def _norm(s: str) -> str:
    """Normalize whitespace."""
    return " ".join(s.split()) if s else ""


def _elem(root: ET.Element | None, path: str, ns: dict | None = None) -> ET.Element | None:
    """Find first child by tag path (no namespace)."""
    if root is None:
        return None
    for tag in path.split("/"):
        found = root.find(tag, ns or {})
        if found is None:
            found = root.find(f".//{tag}", ns or {})
        if found is not None:
            root = found
        else:
            return None
    return root


def _elems(root: ET.Element | None, tag: str) -> list:
    """Find all descendants with tag."""
    if root is None:
        return []
    return list(root.iter(tag))


def _extract_paragraph_text(p_el: ET.Element) -> str:
    """Extract text from paragraph, strip citations (xref ref-type=bibr), convert ext-link to markdown."""
    
    def _process_node(node: ET.Element) -> str:
        """Recursively process a node and its children, skipping citations."""
        parts: list[str] = []
        
        # Add the node's direct text
        if node.text:
            parts.append(node.text)
        
        # Process children
        for child in node:
            if child.tag == "xref" and child.get("ref-type") == "bibr":
                # Skip citation content but keep the tail text
                if child.tail:
                    parts.append(child.tail)
            elif child.tag == "ext-link":
                href = child.get("{http://www.w3.org/1999/xlink}href") or child.get("xlink:href") or ""
                text = _norm(_text(child))
                if href and not href.startswith("#"):
                    parts.append(f"[{text or href}]({href})")
                else:
                    parts.append(text)
                if child.tail:
                    parts.append(child.tail)
            else:
                # Recursively process other elements
                parts.append(_process_node(child))
                if child.tail:
                    parts.append(child.tail)
        
        return "".join(parts)
    
    text = _process_node(p_el)
    text = _norm(text)
    return strip_citations(text)


def _formula_to_latex(formula_el: ET.Element, display: bool) -> str:
    """Extract mml:math from formula element and convert to LaTeX."""
    math_el = formula_el.find(".//{http://www.w3.org/1998/Math/MathML}math")
    if math_el is None:
        math_el = formula_el.find(".//math")
    if math_el is None:
        return ""
    latex = mathml_element_to_latex(math_el)
    if not latex:
        return ""
    return f"$${latex}$$" if display else f"${latex}$"


def _parse_sec(sec_el: ET.Element, level: int) -> Section:
    """Recursively parse a sec element into Section."""
    title_el = sec_el.find("title")
    title = _norm(_text(title_el)) if title_el is not None else ""
    content_parts: list[str] = []
    children: list[Section] = []
    for child in sec_el:
        if child.tag == "title":
            continue
        if child.tag == "sec":
            disp = child.get("disp-level")
            sub_level = int(disp) if disp and disp.isdigit() else level + 1
            children.append(_parse_sec(child, sub_level))
        elif child.tag == "p":
            content_parts.append(_extract_paragraph_text(child))
        elif child.tag == "fig":
            pass  # Figures collected separately
        elif child.tag == "table-wrap":
            pass  # Tables collected separately
        elif child.tag == "disp-formula":
            content_parts.append(_formula_to_latex(child, display=True))
        elif child.tag == "inline-formula":
            content_parts.append(_formula_to_latex(child, display=False))
    content = "\n\n".join(p for p in content_parts if p.strip())
    return Section(title=title, level=level, content=content, children=children)


class XMLParser(BaseParser):
    """Parser for PubMed Central JATS XML articles."""

    def parse(self, content: str) -> Article:
        """Parse XML content into an Article."""
        root = ET.fromstring(content)
        article = root.find("article")
        if article is None:
            article = root
        front = article.find("front")
        article_meta = front.find("article-meta") if front is not None else None
        body = article.find("body")
        back = article.find("back")

        title = _norm(_text(_elem(article_meta, "title-group/article-title")))
        if not title:
            logger.warning("No article title found in XML")
            title = "Untitled"

        doi = None
        for aid in _elems(article_meta or article, "article-id"):
            if aid.get("pub-id-type") == "doi" and aid.text:
                doi = aid.text.strip()
                break

        abstract = self._get_abstract(article_meta)
        sections = self._get_sections(body) if body is not None else []
        figures = self._get_figures(article)
        tables = self._get_tables(article)
        supplementary = self._get_supplementary(back) if back is not None else []

        return Article(
            title=title,
            doi=doi,
            abstract=abstract,
            sections=sections,
            figures=figures,
            tables=tables,
            supplementary=supplementary,
        )

    def _get_abstract(self, article_meta: ET.Element | None) -> str:
        if article_meta is None:
            return ""
        abstract_el = article_meta.find("abstract")
        if abstract_el is None:
            return ""
        parts = []
        for p in abstract_el.findall("p"):
            parts.append(_extract_paragraph_text(p))
        return "\n\n".join(p for p in parts if p.strip())

    def _get_sections(self, body: ET.Element) -> list[Section]:
        sections: list[Section] = []
        for sec in body.findall("sec"):
            disp = sec.get("disp-level")
            level = int(disp) if disp and disp.isdigit() else 1
            if level == 1:
                sections.append(_parse_sec(sec, 1))
        return sections

    def _get_figures(self, article: ET.Element) -> list[Figure]:
        figures: list[Figure] = []
        for fig in article.iter("fig"):
            fid = fig.get("id") or f"F{len(figures)+1}"
            label_el = fig.find("label")
            label = _norm(_text(label_el)) if label_el is not None else ""
            caption_el = fig.find("caption")
            cap_parts = []
            if caption_el is not None:
                for p in caption_el.findall("p"):
                    cap_parts.append(_extract_paragraph_text(p))
                title_el = caption_el.find("title")
                if title_el is not None and _text(title_el):
                    cap_parts.insert(0, _norm(_text(title_el)))
            caption = "\n\n".join(cap_parts)
            figures.append(Figure(id=fid, label=label, caption=caption))
        return figures

    def _get_tables(self, article: ET.Element) -> list[Table]:
        tables: list[Table] = []
        for wrap in article.iter("table-wrap"):
            tid = wrap.get("id") or f"T{len(tables)+1}"
            label_el = wrap.find("label")
            label = _norm(_text(label_el)) if label_el is not None else ""
            cap_el = wrap.find("caption")
            cap_parts = []
            if cap_el is not None:
                for p in cap_el.findall("p"):
                    cap_parts.append(_extract_paragraph_text(p))
            caption = "\n\n".join(cap_parts)
            table_el = wrap.find("table")
            rows: list[list[str]] = []
            if table_el is not None:
                for tr in table_el.findall(".//tr"):
                    row = [_norm(_text(td)) for td in tr.findall("td") + tr.findall("th")]
                    if row:
                        rows.append(row)
            tables.append(Table(id=tid, label=label, caption=caption, data=rows))
        return tables

    def _get_supplementary(self, back: ET.Element) -> list[Supplementary]:
        # Supplementary materials are not loaded per user request
        return []
