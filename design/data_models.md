# Data Models (Intermediate Representation)

The Intermediate Representation (IR) is the core data structure used by the converter. It is implemented using Pydantic for validation and type safety.

## Article Model

The `Article` class is the top-level container for all extracted article data.

```python
class Article(BaseModel):
    title: str
    doi: str | None = None
    
    abstract: str = ""
    sections: list[Section] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    supplementary: list[Supplementary] = Field(default_factory=list)
    
    model_config = {"extra": "forbid"}
```

**Note**: Keywords, authors, affiliations, journal, and publication_date are intentionally excluded to focus on the core scientific content of articles. The DOI field provides a unique identifier that can be used to retrieve full publication metadata if needed.

## Supporting Models

### Section
Sections are recursive to support arbitrary nesting depths (Section -> Subsection -> Sub-subsection).

```python
class Section(BaseModel):
    title: str
    level: int = Field(ge=1, le=6, description="1=section, 2=subsection, ... 6=deepest")
    content: str = ""
    sections: list['Section'] = Field(default_factory=list)
    
    model_config = {"extra": "forbid"}
```

### Figure & Table
Captures metadata and content for non-textual elements.

```python
class Figure(BaseModel):
    id: str
    label: str
    caption: str

class Table(BaseModel):
    id: str
    label: str
    caption: str
    data: list[list[str]] = Field(default_factory=list)  # 2D list for table rows/columns
```

### Supplementary
```python
class Supplementary(BaseModel):
    label: str
    description: str
```

## Transformation Rules
- **Citations**: Removed during parsing.
- **Math**: Converted to LaTeX and stored as `$math$` (inline) or `$$math$$` (display) within the `content` field of `Section`.
- **Links**: Converted to Markdown `[text](url)` format.
