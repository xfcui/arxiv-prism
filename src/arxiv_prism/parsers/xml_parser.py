"""XML parser for PubMed Central JATS format."""

import logging
import re
from xml.etree import ElementTree as ET

from arxiv_prism.models import (
    Article,
    Author,
    Figure,
    Section,
    Table,
)
from arxiv_prism.models import Supplementary  # noqa: F401 - used in return type
from arxiv_prism.parsers.base import BaseParser
from arxiv_prism.text_utils import strip_citations, link_to_markdown
from arxiv_prism.math_utils import mathml_element_to_latex

logger = logging.getLogger(__name__)

NS = {
    "mml": "http://www.w3.org/1998/Math/MathML",
    "xlink": "http://www.w3.org/1999/xlink",
    "dc": "http://purl.org/dc/elements/1.1/",
    "prism": "http://prismstandard.org/namespaces/basic/2.0/",
    "ce": "http://www.elsevier.com/xml/common/dtd",
    "svapi": "http://www.elsevier.com/xml/svapi/article/dtd",
}


def _text(el: ET.Element | None) -> str:
    """Recursive text of element and children."""
    if el is None:
        return ""
    # Use list() to ensure we can check if it's empty, or just join
    return " ".join(el.itertext())


def _norm(s: str) -> str:
    """Normalize whitespace."""
    return " ".join(s.split()) if s else ""


def _elem(root: ET.Element | None, path: str, ns: dict | None = None) -> ET.Element | None:
    """Find first child by tag path (no namespace)."""
    if root is None:
        return None
    namespaces = ns or NS
    for tag in path.split("/"):
        # Try with namespace if tag has prefix
        if ":" in tag:
            prefix, local = tag.split(":", 1)
            if prefix in namespaces:
                tag = f"{{{namespaces[prefix]}}}{local}"
        
        found = root.find(tag, namespaces)
        if found is None:
            found = root.find(f".//{tag}", namespaces)
        if found is not None:
            root = found
        else:
            return None
    return root


def _elems(root: ET.Element | None, tag: str, ns: dict | None = None) -> list:
    """Find all descendants with tag."""
    if root is None:
        return []
    namespaces = ns or NS
    if ":" in tag:
        prefix, local = tag.split(":", 1)
        if prefix in namespaces:
            tag = f"{{{namespaces[prefix]}}}{local}"
    return list(root.iter(tag))


_MONTH_ABBR = {
    "1": "Jan", "2": "Feb", "3": "Mar", "4": "Apr",
    "5": "May", "6": "Jun", "7": "Jul", "8": "Aug",
    "9": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
    "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
    "09": "Sep",
}


def _format_pubdate(year: str, month: str, day: str) -> str:
    """Format pubdate to 'YYYY Mon D' matching NCBI format."""
    year = year.strip()
    month = month.strip()
    day = day.strip().lstrip("0") or day.strip()  # remove leading zero from day
    month = _MONTH_ABBR.get(month, month)  # convert numeric month to abbreviation
    parts = [p for p in [year, month, day] if p]
    return " ".join(parts)


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
            tag = child.tag
            if isinstance(tag, str) and "}" in tag:
                tag = tag.split("}", 1)[1]

            if tag == "xref" and child.get("ref-type") == "bibr":
                # Skip citation content but keep the tail text
                if child.tail:
                    parts.append(child.tail)
            elif tag in ("inline-formula", "disp-formula"):
                # Convert math to LaTeX within paragraphs
                parts.append(_formula_to_latex(child, display=(tag == "disp-formula")))
                if child.tail:
                    parts.append(child.tail)
            elif tag in ("ext-link", "link"):
                href = child.get("{http://www.w3.org/1999/xlink}href") or child.get("xlink:href") or child.get("href") or ""
                text = _norm(_text(child))
                parts.append(link_to_markdown(href, text))
                if child.tail:
                    parts.append(child.tail)
            elif tag == "italic" or tag == "bold":
                # Handle basic formatting if needed, but for now just text
                parts.append(_process_node(child))
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
    # Add spaces around delimiters for better markdown rendering and to prevent text bleeding
    return f" $${latex}$$ " if display else f" ${latex}$ "


def _parse_sec(sec_el: ET.Element, level: int) -> Section:
    """Recursively parse a sec element into Section."""
    title_el = sec_el.find("title") or sec_el.find("{http://www.elsevier.com/xml/common/dtd}section-title")
    title = _norm(_text(title_el)) if title_el is not None else ""
    content_parts: list[str] = []
    sections: list[Section] = []
    for child in sec_el:
        tag = child.tag
        if isinstance(tag, str) and "}" in tag:
            tag = tag.split("}", 1)[1]

        if tag in ("title", "section-title"):
            continue
        if tag in ("sec", "sections"):
            disp = child.get("disp-level")
            sub_level = int(disp) if disp and disp.isdigit() else level + 1
            sections.append(_parse_sec(child, sub_level))
        elif tag in ("p", "para"):
            content_parts.append(_extract_paragraph_text(child))
        elif tag == "fig":
            pass  # Figures collected separately
        elif tag == "table-wrap":
            pass  # Tables collected separately
        elif tag == "disp-formula":
            content_parts.append(_formula_to_latex(child, display=True))
        elif tag == "inline-formula":
            content_parts.append(_formula_to_latex(child, display=False))
    content = "\n\n".join(p for p in content_parts if p.strip())
    return Section(title=title, level=level, content=content, sections=sections)


class XMLParser(BaseParser):
    """Parser for PubMed Central JATS XML articles."""

    def parse(self, content: str) -> Article:
        """Parse XML content into an Article."""
        root = ET.fromstring(content)
        
        # Determine format
        if "elsevier.com" in content:
            return self._parse_elsevier(root)
        
        article = root.find("article")
        if article is None:
            # Wrapped formats (e.g. Springer Nature <response><records><article>)
            article = root.find(".//article")
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
        pmid = None
        pmcid = None
        for aid in _elems(article_meta or article, "article-id"):
            id_type = aid.get("pub-id-type")
            if id_type == "doi" and aid.text:
                doi = aid.text.strip()
            elif id_type == "pmid" and aid.text:
                pmid = aid.text.strip()
            elif id_type == "pmcid" and aid.text:
                pmcid = aid.text.strip()

        # Extract authors
        authors = []
        contrib_group = _elem(article_meta, "contrib-group")
        if contrib_group is not None:
            for contrib in _elems(contrib_group, "contrib"):
                if contrib.get("contrib-type") == "author":
                    name_el = contrib.find("name")
                    if name_el is not None:
                        surname = _text(name_el.find("surname"))
                        given = _text(name_el.find("given-names"))
                        # Match NCBI format: Surname Given (no comma)
                        authors.append(Author(name=f"{surname} {given}".strip()))
                    else:
                        # Handle cases where name is directly in contrib or string-name
                        string_name = contrib.find("string-name")
                        if string_name is not None:
                            name = _norm(_text(string_name))
                            # Try to convert "First Last" to "Last First" if it looks like it
                            # and doesn't already have a comma
                            if "," not in name:
                                parts = name.split()
                                if len(parts) == 2:
                                    name = f"{parts[1]} {parts[0]}"
                                elif len(parts) > 2:
                                    name = f"{parts[-1]} {' '.join(parts[:-1])}"
                            else:
                                # If it has a comma "Last, First", convert to "Last First"
                                name = " ".join(p.strip() for p in name.split(","))
                            authors.append(Author(name=name))

        # Extract pub-dates by type to match NCBI field mapping:
        #   collection → pubdate + printpubdate (journal issue date)
        #   pub/electronic → epubdate (online-first date)
        #   pub/print → pubdate + printpubdate (for print journals like Springer Nature)
        collection_date = epub_date = print_date = fallback_date = None
        for pub_date_el in _elems(article_meta or article, "pub-date"):
            year = _text(pub_date_el.find("year"))
            month = _text(pub_date_el.find("month"))
            day = _text(pub_date_el.find("day"))
            if not year:
                continue
            date_str = _format_pubdate(year, month, day)
            pub_type = pub_date_el.get("date-type") or pub_date_el.get("pub-type") or ""
            pub_fmt = pub_date_el.get("publication-format") or ""
            if pub_type == "collection":
                collection_date = date_str
            elif "electronic" in pub_fmt or "epub" in pub_type or "electronic" in pub_type:
                epub_date = date_str
            elif "print" in pub_fmt or "ppub" in pub_type:
                print_date = date_str
            else:
                fallback_date = date_str

        # Resolve final dates matching NCBI pattern
        epubdate = epub_date or ""
        # Only use collection_date when it has at least year+month; year-only is too imprecise
        if collection_date and len(collection_date.split()) > 1:
            # Online journal with volume/issue collection date (e.g. NCBI Sci_Adv, Genome_Biol)
            pubdate = collection_date
            printpubdate = collection_date
        elif print_date:
            # Print+online journal (e.g. Springer Nature)
            pubdate = print_date
            printpubdate = print_date
        elif epub_date:
            # Online-only journal (e.g. NCBI Nat_Commun)
            pubdate = epub_date
            printpubdate = ""
        else:
            pubdate = fallback_date
            printpubdate = fallback_date or ""

        # Extract volume, issue, pages from article-meta
        meta_el = article_meta or article
        volume = _norm(_text(_elem(meta_el, "volume")))
        issue = _norm(_text(_elem(meta_el, "issue")))
        fpage = _norm(_text(_elem(meta_el, "fpage")))
        lpage = _norm(_text(_elem(meta_el, "lpage")))
        eloc = _norm(_text(_elem(meta_el, "elocation-id")))
        # For print journals use page range; for online-only use elocation-id
        if print_date and fpage:
            pages = f"{fpage}-{lpage}" if lpage and lpage != fpage else fpage
        elif eloc:
            pages = eloc
        elif fpage:
            pages = f"{fpage}-{lpage}" if lpage and lpage != fpage else fpage
        else:
            pages = ""

        abstract = self._get_abstract(article_meta)
        sections = self._get_sections(body) if body is not None else []
        figures = self._get_figures(article)
        tables = self._get_tables(article)
        supplementary = self._get_supplementary(back) if back is not None else []

        return Article(
            title=title,
            doi=doi,
            pmid=pmid,
            pmcid=pmcid,
            pubdate=pubdate,
            epubdate=epubdate,
            printpubdate=printpubdate,
            authors=authors,
            abstract=abstract,
            sections=sections,
            figures=figures,
            tables=tables,
            supplementary=supplementary,
            volume=volume,
            issue=issue,
            pages=pages,
        )

    def _parse_elsevier(self, root: ET.Element) -> Article:
        svapi = NS["svapi"]
        coredata = root.find(f"{{{svapi}}}coredata")
        original_text = root.find(f"{{{svapi}}}originalText")

        title = _norm(_text(_elem(coredata, "dc:title")))
        doi = _norm(_text(_elem(coredata, "prism:doi")))
        pmid_el = root.find(f"{{{svapi}}}pubmed-id")
        pmid = _norm(pmid_el.text) if pmid_el is not None and pmid_el.text else ""

        authors = []
        for creator in _elems(coredata, "dc:creator"):
            name = _norm(creator.text or "")
            if "," in name:
                # Normalize "Surname, Given" → "Surname Given" to match NCBI format
                parts = [p.strip() for p in name.split(",", 1)]
                name = " ".join(p for p in parts if p)
            if name:
                authors.append(Author(name=name))

        # Normalize coverDate from ISO "2022-05-10" to "YYYY Mon D" matching NCBI format
        cover_date_raw = _norm(_text(_elem(coredata, "prism:coverDate")))
        if cover_date_raw and re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", cover_date_raw):
            year, month, day = cover_date_raw.split("-")
            pubdate = _format_pubdate(year, month, day)
        else:
            pubdate = cover_date_raw or None

        volume = _norm(_text(_elem(coredata, "prism:volume")))
        issue = _norm(_text(_elem(coredata, "prism:issueIdentifier")))
        pages = _norm(_text(_elem(coredata, "prism:pageRange")))

        abstract_parts = []
        for abs_el in _elems(coredata, "dc:description"):
            abstract_parts.append(_extract_paragraph_text(abs_el))
        abstract = "\n\n".join(p for p in abstract_parts if p.strip())
        
        sections = []
        if original_text is not None:
            for sec in _elems(original_text, "ce:sections"):
                sections.append(_parse_sec(sec, 1))
        
        figures = []
        for fig in _elems(root, "ce:figure"):
            fid = fig.get("id") or f"F{len(figures)+1}"
            label = _norm(_text(fig.find("{http://www.elsevier.com/xml/common/dtd}label")))
            caption_el = fig.find("{http://www.elsevier.com/xml/common/dtd}caption")
            cap_parts = []
            if caption_el is not None:
                for p in caption_el.findall("{http://www.elsevier.com/xml/common/dtd}simple-para"):
                    cap_parts.append(_extract_paragraph_text(p))
            caption = "\n\n".join(cap_parts)
            figures.append(Figure(id=fid, label=label, caption=caption))
            
        tables = []
        # Elsevier tables are complex, but let's try to get simple ones
        for wrap in _elems(root, "ce:table"):
            tid = wrap.get("id") or f"T{len(tables)+1}"
            label = _norm(_text(wrap.find("{http://www.elsevier.com/xml/common/dtd}label")))
            cap_el = wrap.find("{http://www.elsevier.com/xml/common/dtd}caption")
            cap_parts = []
            if cap_el is not None:
                for p in cap_el.findall("{http://www.elsevier.com/xml/common/dtd}simple-para"):
                    cap_parts.append(_extract_paragraph_text(p))
            caption = "\n\n".join(cap_parts)
            
            rows = []
            # Elsevier uses CALS or other table models, might be hard to parse simply
            # For now, just placeholder or basic parse if possible
            tables.append(Table(id=tid, label=label, caption=caption, data=rows))
            
        # prism:coverDate is the print cover date; set printpubdate to match NCBI
        # pattern for print journals (pubdate == printpubdate, epubdate == "")
        printpubdate = pubdate or ""

        return Article(
            title=title,
            doi=doi,
            pmid=pmid,
            pubdate=pubdate,
            printpubdate=printpubdate,
            authors=authors,
            abstract=abstract,
            sections=sections,
            figures=figures,
            tables=tables,
            volume=volume,
            issue=issue,
            pages=pages,
        )

    def _get_abstract(self, article_meta: ET.Element | None) -> str:
        if article_meta is None:
            return ""
        abstract_el = article_meta.find("abstract")
        if abstract_el is None:
            return ""
        parts = []
        for p in abstract_el.findall("p") + abstract_el.findall("para"):
            parts.append(_extract_paragraph_text(p))
        return "\n\n".join(p for p in parts if p.strip())

    def _get_sections(self, body: ET.Element) -> list[Section]:
        sections: list[Section] = []
        for sec in body.findall("sec") + body.findall("sections"):
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
