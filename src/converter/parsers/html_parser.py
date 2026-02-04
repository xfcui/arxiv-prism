"""HTML parser for Nature/Springer journal articles."""

import logging
import re
from bs4 import BeautifulSoup

from converter.models import (
    Affiliation,
    Article,
    Author,
    Figure,
    Section,
    Supplementary,
    Table,
)
from converter.parsers.base import BaseParser
from converter.text_utils import strip_citations

logger = logging.getLogger(__name__)

# Section titles to skip (reference list, etc.)
SKIP_SECTION_TITLES = {"References", "References "}


def _element_text(el) -> str:
    """Get text from element, stripping extra whitespace."""
    if el is None:
        return ""
    return " ".join(el.get_text(separator=" ", strip=True).split())


def _extract_text_with_links(soup, el) -> str:
    """Extract text from element, converting <a> to [text](url)."""
    if el is None:
        return ""
    parts = []
    for child in el.descendants:
        if child.name == "a" and child.get("href"):
            href = child.get("href", "")
            if not href.startswith("#"):
                text = child.get_text(strip=True)
                parts.append(f"[{text}]({href})")
                return " ".join(parts) + " " + _element_text(el)
        if isinstance(child, str):
            parts.append(child)
    return _element_text(el)


def _clean_content_text(soup, container) -> str:
    """Extract clean text: strip citations (sup/ref links), convert links to markdown."""
    if container is None:
        return ""
    # Clone to avoid modifying original
    container = BeautifulSoup(str(container), "lxml").find()
    if not container:
        return ""
    # Remove citation refs: sup containing links to #ref-
    for sup in container.find_all("sup"):
        ref_link = sup.find("a", href=re.compile(r"#ref-|#cite", re.I))
        if ref_link:
            sup.decompose()
    # Remove standalone citation links
    for a in container.find_all("a", href=re.compile(r"#ref-|#cite", re.I)):
        a.decompose()
    # Convert remaining links to [text](url)
    for a in container.find_all("a", href=True):
        href = a.get("href", "")
        if href.startswith("#"):
            # Internal anchor - keep text only
            a.replace_with(a.get_text(strip=True))
        else:
            text = a.get_text(strip=True) or href
            a.replace_with(f"[{text}]({href})")
    text = container.get_text(separator=" ", strip=True)
    text = re.sub(r"  +", " ", text)
    text = strip_citations(text)
    return text.strip()


class HTMLParser(BaseParser):
    """Parser for Nature/Springer HTML article pages."""

    def parse(self, content: str) -> Article:
        """Parse HTML content into an Article."""
        soup = BeautifulSoup(content, "lxml")
        title = self._get_title(soup)
        if not title:
            logger.warning("No article title found in HTML")
            title = "Untitled"
        doi = self._get_doi(soup)
        journal = self._get_journal(soup)
        pub_date = self._get_publication_date(soup)
        keywords = self._get_keywords(soup)
        authors, affiliations = self._get_authors_affiliations(soup)
        abstract = self._get_abstract(soup)
        sections = self._get_sections(soup)
        figures = self._get_figures(soup)
        tables = self._get_tables(soup)
        supplementary = self._get_supplementary(soup)
        return Article(
            title=title,
            doi=doi,
            journal=journal,
            publication_date=pub_date,
            keywords=keywords,
            authors=authors,
            affiliations=affiliations,
            abstract=abstract,
            sections=sections,
            figures=figures,
            tables=tables,
            supplementary=supplementary,
        )

    def _get_title(self, soup: BeautifulSoup) -> str:
        el = soup.select_one("h1.c-article-title")
        return _element_text(el) if el else ""

    def _get_doi(self, soup: BeautifulSoup) -> str | None:
        meta = soup.find("meta", attrs={"name": "DOI"})
        if meta and meta.get("content"):
            return meta["content"].strip()
        return None

    def _get_journal(self, soup: BeautifulSoup) -> str | None:
        meta = soup.find("meta", attrs={"name": "citation_journal_title"})
        if meta and meta.get("content"):
            return meta["content"].strip()
        return None

    def _get_publication_date(self, soup: BeautifulSoup) -> str | None:
        meta = soup.find("meta", attrs={"name": "citation_publication_date"})
        if meta and meta.get("content"):
            return meta["content"].strip()
        return None

    def _get_keywords(self, soup: BeautifulSoup) -> list[str]:
        meta = soup.find("meta", attrs={"name": "citation_keywords"})
        if meta and meta.get("content"):
            return [k.strip() for k in meta["content"].split(",") if k.strip()]
        return []

    def _get_authors_affiliations(
        self, soup: BeautifulSoup
    ) -> tuple[list[Author], list[Affiliation]]:
        affiliations: list[Affiliation] = []
        seen_aff: dict[str, int] = {}
        aff_id = 0
        for meta in soup.find_all("meta", attrs={"name": "citation_author_institution"}):
            content = meta.get("content", "").strip()
            if content and content not in seen_aff:
                aff_id += 1
                seen_aff[content] = aff_id
                affiliations.append(Affiliation(id=aff_id, text=content))
        authors: list[Author] = []
        author_metas = soup.find_all("meta", attrs={"name": "citation_author"})
        inst_metas = soup.find_all("meta", attrs={"name": "citation_author_institution"})
        for i, meta in enumerate(author_metas):
            name = (meta.get("content") or "").strip()
            if not name:
                continue
            aff_indices: list[int] = []
            if i < len(inst_metas):
                inst = (inst_metas[i].get("content") or "").strip()
                if inst and inst in seen_aff:
                    aff_indices.append(seen_aff[inst])
            authors.append(Author(name=name, affiliations=aff_indices))
        if authors:
            return authors, affiliations
        # Fallback: parse author list and href for Aff1, Aff2
        for a in soup.select("ul.c-article-author-list a[data-test=author-name]"):
            name = _element_text(a)
            if not name or name == "…":
                continue
            href = a.get("href", "")
            aff_indices = []
            match = re.search(r"Aff(\d+)", href, re.I)
            if match:
                aff_indices.append(int(match.group(1)))
            authors.append(Author(name=name, affiliations=aff_indices))
        for el in soup.find_all(id=re.compile(r"^Aff\d+$")):
            aid = el.get("id", "")
            n = re.match(r"Aff(\d+)", aid)
            if n:
                idx = int(n.group(1))
                text = _element_text(el)
                if text and not any(a.id == idx for a in affiliations):
                    affiliations.append(Affiliation(id=idx, text=text))
        affiliations.sort(key=lambda x: x.id)
        return authors, affiliations

    def _get_abstract(self, soup: BeautifulSoup) -> str:
        section = soup.find("section", attrs={"data-title": "Abstract"})
        if not section:
            return ""
        content = section.select_one(".c-article-section__content")
        return _clean_content_text(soup, content) if content else ""

    def _get_sections(self, soup: BeautifulSoup) -> list[Section]:
        sections_out: list[Section] = []
        for section_el in soup.find_all("section", attrs={"data-title": True}):
            title_attr = section_el.get("data-title", "").strip()
            if title_attr in SKIP_SECTION_TITLES:
                continue
            h2 = section_el.select_one("h2.c-article-section__title")
            title = _element_text(h2) if h2 else title_attr
            content_div = section_el.select_one(".c-article-section__content")
            if not content_div:
                sections_out.append(
                    Section(title=title, level=1, content="", children=[])
                )
                continue
            blocks: list[tuple[int, str, str, list]] = []
            current_level = 1
            current_title = title
            current_parts: list[str] = []
            for node in content_div.children:
                if not getattr(node, "name", None):
                    continue
                if node.name == "h2" and "c-article__sub-heading" in (
                    node.get("class") or []
                ):
                    if current_title or current_parts:
                        content = "\n\n".join(p for p in current_parts if p.strip())
                        blocks.append((current_level, current_title, content, []))
                    current_level, current_title = 2, _element_text(node)
                    current_parts = []
                elif node.name == "h3":
                    if current_title or current_parts:
                        content = "\n\n".join(p for p in current_parts if p.strip())
                        blocks.append((current_level, current_title, content, []))
                    current_level, current_title = 2, _element_text(node)
                    current_parts = []
                elif node.name == "h4":
                    if current_title or current_parts:
                        content = "\n\n".join(p for p in current_parts if p.strip())
                        blocks.append((current_level, current_title, content, []))
                    current_level, current_title = 3, _element_text(node)
                    current_parts = []
                elif node.name in ("p", "div"):
                    if node.find_parent("figure") or node.find_parent("table"):
                        continue
                    text = _clean_content_text(soup, node)
                    if text:
                        current_parts.append(text)
            if current_title or current_parts:
                content = "\n\n".join(p for p in current_parts if p.strip())
                blocks.append((current_level, current_title, content, []))
            if not blocks:
                sections_out.append(
                    Section(title=title, level=1, content="", children=[])
                )
                continue
            # Build tree: first block is level 1, then level 2/3 are children
            first_content = blocks[0][2] if blocks else ""
            children: list[Section] = []
            i = 1
            while i < len(blocks):
                lv, tt, ct, _ = blocks[i]
                if lv == 2:
                    sub_children: list[Section] = []
                    j = i + 1
                    while j < len(blocks) and blocks[j][0] == 3:
                        sub_children.append(
                            Section(
                                title=blocks[j][1],
                                level=3,
                                content=blocks[j][2],
                                children=[],
                            )
                        )
                        j += 1
                    children.append(
                        Section(
                            title=tt, level=2, content=ct, children=sub_children
                        )
                    )
                    i = j
                else:
                    i += 1
            sections_out.append(
                Section(
                    title=title,
                    level=1,
                    content=first_content,
                    children=children,
                )
            )
        return sections_out

    def _get_figures(self, soup: BeautifulSoup) -> list[Figure]:
        figures: list[Figure] = []
        for fig in soup.find_all("figure"):
            cap_el = fig.find("figcaption") or fig.find(class_=re.compile("caption"))
            caption = _element_text(cap_el) if cap_el else ""
            label_el = fig.find(class_=re.compile("label|figure-number"))
            label = _element_text(label_el) if label_el else ""
            fid = fig.get("id") or fig.get("data-id") or ""
            if not fid and (label or caption):
                fid = f"F{len(figures)+1}"
            if label or caption:
                figures.append(
                    Figure(id=fid or f"F{len(figures)+1}", label=label, caption=caption)
                )
        return figures

    def _get_tables(self, soup: BeautifulSoup) -> list[Table]:
        tables: list[Table] = []
        for table_el in soup.find_all("table"):
            rows: list[list[str]] = []
            thead = table_el.find("thead")
            if thead:
                for tr in thead.find_all("tr"):
                    rows.append(
                        [_element_text(th) for th in tr.find_all(["th", "td"])]
                    )
            for tr in table_el.find_all("tbody", recursive=False):
                for r in tr.find_all("tr"):
                    rows.append(
                        [_element_text(td) for td in r.find_all(["td", "th"])]
                    )
            if not rows and table_el.find("tr"):
                for tr in table_el.find_all("tr"):
                    rows.append(
                        [_element_text(c) for c in tr.find_all(["th", "td"])]
                    )
            if rows:
                tables.append(
                    Table(
                        id=f"T{len(tables)+1}",
                        label="",
                        caption="",
                        data=rows,
                    )
                )
        return tables

    def _get_supplementary(self, soup: BeautifulSoup) -> list[Supplementary]:
        supp: list[Supplementary] = []
        section = soup.find("section", attrs={"data-title": "Supplementary information"})
        if not section:
            return supp
        content = section.select_one(".c-article-section__content")
        if not content:
            return supp
        for a in content.find_all("a", href=True):
            text = _element_text(a)
            href = a.get("href", "")
            if text and ("supplementary" in href.lower() or "supp" in text.lower()):
                supp.append(Supplementary(label=text[:80], description=href))
        return supp
