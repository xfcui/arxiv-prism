# Formatters Design

Formatters take the `Article` IR and generate the final output string.

## Base Formatter

All formatters inherit from `BaseFormatter`.

```python
class BaseFormatter(ABC):
    @abstractmethod
    def format(self, article: Article) -> str:
        pass
```

## JSON Formatter

Serializes the `Article` model directly to JSON.

- **Output**: A single JSON file.
- **Options**: Support for pretty-printing (indentation).

## Markdown Formatter

Generates a human-readable Markdown file.

### Formatting Rules
- **Header**: Includes title, authors, DOI, and journal info.
- **Sections**: Uses `#`, `##`, `###` based on section level.
- **Figures**: Rendered as a block with label and caption, plus an `(image omitted)` note.
- **Tables**: Converted to standard Markdown table syntax.
- **Math**: Preserved as LaTeX `$inline$` or `$$display$$`.
- **Supplementary**: Listed at the end of the document.

### Example Figure Output
```markdown
**Figure 1**: Schematic of the experimental setup.

*(image omitted)*
```

### Example Table Output
```markdown
**Table 1**: Model results.

| Metric | Value |
|--------|-------|
| Acc    | 0.98  |
```
