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
- **Authors**: `ul.c-article-author-list` with `a[data-test="author-name"]`
- **Affiliations**: Elements with `id="AffX"`
- **Sections**: `section[data-title]` with `h2.c-article-section__title`
- **Sub-headings**: `h3.c-article__sub-heading`

## XML Parser (JATS/PMC)

Targeted at PubMed Central JATS XML format.

### Extraction Logic
- **Title**: `<article-title>`
- **DOI**: `<article-id pub-id-type="doi">`
- **Authors**: `<contrib contrib-type="author">`
- **Affiliations**: `<aff id="affX">`
- **Sections**: `<sec>` elements with `disp-level` attributes.
- **Figures/Tables**: `<fig>` and `<table-wrap>` elements.

## Common Challenges
- **Math Conversion**: Both parsers use `latex2mathml` (or similar) to convert MathML blocks into LaTeX strings.
- **Cleaning**: Removing citations (e.g., `[1]`, `(Smith et al., 2020)`) and reference lists.
- **Encoding**: Ensuring UTF-8 handling for special characters.
