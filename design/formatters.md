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

Serializes the `Article` model directly to JSON via `model_dump(mode="json")`.

- **Output**: Compact JSON (no indentation), UTF-8 with `ensure_ascii=False`.

## Markdown Formatter

Generates a human-readable Markdown file.

### Formatting Rules
- **Header**: Includes title and DOI.
- **Sections**: Heading level = `heading_base + section.level - 1`, capped at 6 (`#`…`######`). Nested sections rendered recursively via `section.sections`.
- **Figures**: Rendered as a block with label and caption, plus an `(image omitted)` note.
- **Tables**: Converted to standard Markdown table syntax.
- **Math**: Preserved as LaTeX `$inline$` or `$$display$$`.
- **Supplementary**: Listed at the end of the document if present.

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
