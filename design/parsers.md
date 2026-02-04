# Parsers Design

Parsers are responsible for converting raw input files (HTML/XML) into the `Article` IR.

## Base Parser

All parsers inherit from `BaseParser`, which defines the contract.

```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: str) -> Article:
        pass
```

## HTML Parser (Nature/Springer)

Targeted at Nature and Springer article formats.

### Extraction Logic
- **Title**: `h1.c-article-title`
- **DOI**: `meta[name="DOI"]`
- **Abstract**: `section[data-title="Abstract"]`
- **Sections**: `section[data-title]` with `h2.c-article-section__title`
- **Sub-headings**: `h3.c-article__sub-heading`
- **Figures**: `<figure>` elements with captions
- **Tables**: `<table>` elements

**Note**: Authors, affiliations, keywords, journal, and publication date are not extracted.

## XML Parser (JATS/PMC)

Targeted at PubMed Central JATS XML format.

### Extraction Logic
- **Title**: `<article-title>`
- **DOI**: `<article-id pub-id-type="doi">`
- **Abstract**: `<abstract>` with `<p>` paragraphs
- **Sections**: `<sec>` elements with `disp-level` attributes
- **Figures/Tables**: `<fig>` and `<table-wrap>` elements
- **Math**: MathML converted to LaTeX

**Note**: Authors, affiliations, keywords, journal, and publication date are not extracted.

## Common Challenges
- **Math Conversion**: Both parsers use `mathml_element_to_latex` to convert MathML blocks into LaTeX strings.
- **Cleaning**: Removing citations (e.g., `[1]`, `(Smith et al., 2020)`) and reference lists.
- **Encoding**: Ensuring UTF-8 handling for special characters.
- **Supplementary Materials**: Currently not extracted per user request (returns empty list).
