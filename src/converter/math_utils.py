"""MathML to LaTeX conversion (minimal implementation)."""

import re
from xml.etree import ElementTree as ET

# MathML namespace
MML_NS = "http://www.w3.org/1998/Math/MathML"


def _text(el: ET.Element) -> str:
    return "".join(el.itertext()) if el.itertext else ""


def _mathml_to_latex_el(el: ET.Element) -> str:
    """Convert a single MathML element to LaTeX."""
    tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
    if tag == "math":
        body = "".join(_mathml_to_latex_el(c) for c in el)
        return body.strip()
    if tag == "mrow":
        return "".join(_mathml_to_latex_el(c) for c in el)
    if tag == "mi":
        s = _text(el).strip()
        if len(s) == 1:
            return s
        return "\\" + s + " "
    if tag == "mn":
        return _text(el).strip()
    if tag == "mo":
        op = _text(el).strip()
        if op in ("+", "-", "=", "<", ">", "*", "/", "(", ")", "[", "]", "{", "}", "|", ",", ".", ":", ";"):
            return op
        if op == "−":
            return "-"
        if op == "×":
            return "\\times "
        if op == "÷":
            return "\\div "
        if op == "≤" or op == "⩽":
            return "\\leq "
        if op == "≥" or op == "⩾":
            return "\\geq "
        if op == "≠":
            return "\\neq "
        if op == "±":
            return "\\pm "
        if op == "∓":
            return "\\mp "
        if op == "∈":
            return "\\in "
        if op == "∉":
            return "\\notin "
        if op == "⊂":
            return "\\subset "
        if op == "⊃":
            return "\\supset "
        if op == "⊆":
            return "\\subseteq "
        if op == "⊇":
            return "\\supseteq "
        if op == "∪":
            return "\\cup "
        if op == "∩":
            return "\\cap "
        if op == "∞":
            return "\\infty "
        if op == "∑":
            return "\\sum "
        if op == "∏":
            return "\\prod "
        if op == "∫":
            return "\\int "
        return op
    if tag == "msup":
        children = list(el)
        base = _mathml_to_latex_el(children[0]) if children else ""
        exp = _mathml_to_latex_el(children[1]) if len(children) > 1 else ""
        return f"{{{base}}}^{{{exp}}}"
    if tag == "msub":
        children = list(el)
        base = _mathml_to_latex_el(children[0]) if children else ""
        sub = _mathml_to_latex_el(children[1]) if len(children) > 1 else ""
        return f"{{{base}}}_{{{sub}}}"
    if tag == "mfrac":
        children = list(el)
        num = _mathml_to_latex_el(children[0]) if children else ""
        den = _mathml_to_latex_el(children[1]) if len(children) > 1 else ""
        return f"\\frac{{{num}}}{{{den}}}"
    if tag == "msqrt":
        body = "".join(_mathml_to_latex_el(c) for c in el)
        return f"\\sqrt{{{body}}}"
    if tag == "mroot":
        children = list(el)
        body = _mathml_to_latex_el(children[0]) if children else ""
        n = _mathml_to_latex_el(children[1]) if len(children) > 1 else "2"
        return f"\\sqrt[{n}]{{{body}}}"
    if tag == "mover":
        children = list(el)
        base = _mathml_to_latex_el(children[0]) if children else ""
        acc = _mathml_to_latex_el(children[1]) if len(children) > 1 else ""
        return f"\\overline{{{base}}}" if acc in ("-", "¯") else f"\\overset{{{acc}}}{{{base}}}"
    if tag == "munder":
        children = list(el)
        base = _mathml_to_latex_el(children[0]) if children else ""
        und = _mathml_to_latex_el(children[1]) if len(children) > 1 else ""
        return f"\\underset{{{und}}}{{{base}}}"
    if tag == "msubsup":
        children = list(el)
        base = _mathml_to_latex_el(children[0]) if children else ""
        sub = _mathml_to_latex_el(children[1]) if len(children) > 1 else ""
        sup = _mathml_to_latex_el(children[2]) if len(children) > 2 else ""
        return f"{{{base}}}_{{{sub}}}^{{{sup}}}"
    if tag == "mtable":
        # Find mtr rows by iterating and checking stripped tag (handles namespaces)
        rows = [child for child in el if child.tag.split("}")[-1] == "mtr"]
        if not rows:
            return "[table]"
        # Process each row, finding mtd cells similarly
        row_parts = []
        for row in rows:
            cells = [child for child in row if child.tag.split("}")[-1] == "mtd"]
            if cells:
                row_parts.append(" & ".join(_mathml_to_latex_el(c) for c in cells))
        if not row_parts:
            return "[table]"
        return "\\begin{matrix}" + " \\\\ ".join(row_parts) + "\\end{matrix}"
    if tag in ("mtr", "mtd"):
        return "".join(_mathml_to_latex_el(c) for c in el)
    if tag == "mfenced":
        open_ = el.get("open", "(")
        close = el.get("close", ")")
        body = ",".join(_mathml_to_latex_el(c) for c in el)
        return open_ + body + close
    if tag == "munderover":
        children = list(el)
        base = _mathml_to_latex_el(children[0]) if children else ""
        und = _mathml_to_latex_el(children[1]) if len(children) > 1 else ""
        ov = _mathml_to_latex_el(children[2]) if len(children) > 2 else ""
        return f"\\underset{{{und}}}{{\\overset{{{ov}}}{{{base}}}}}"
    if tag == "mtext":
        # Extract text content directly for text in formulas
        text = _text(el).strip()
        if text:
            return f"\\text{{{text}}}"
        return ""
    if tag == "mspace":
        # Handle spacing - map width attribute to LaTeX spacing commands
        width = el.get("width", "")
        if "thin" in width or width in ("0.167em", "3pt"):
            return "\\,"
        if "medium" in width or width in ("0.222em", "4pt"):
            return "\\:"
        if "thick" in width or width in ("0.278em", "5pt"):
            return "\\;"
        if "1em" in width:
            return "\\quad "
        if "2em" in width:
            return "\\qquad "
        return " "  # Default spacing
    return "".join(_mathml_to_latex_el(c) for c in el)


def mathml_to_latex(mathml_str: str) -> str:
    """Convert MathML string to LaTeX. Returns placeholder on failure."""
    if not mathml_str or not mathml_str.strip():
        return ""
    try:
        root = ET.fromstring(mathml_str)
        return _mathml_to_latex_el(root).strip()
    except ET.ParseError:
        return ""
    except Exception:
        return ""


def mathml_element_to_latex(el: ET.Element) -> str:
    """Convert a MathML element to LaTeX."""
    return _mathml_to_latex_el(el).strip()
