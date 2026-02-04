# Data Models (Intermediate Representation)

The Intermediate Representation (IR) is the core data structure used by the converter. It is implemented using Pydantic for validation and type safety.

## Article Model

The `Article` class is the top-level container for all extracted article data.

```python
class Article(BaseModel):
    title: str
    doi: Optional[str] = None
    journal: Optional[str] = None
    publication_date: Optional[str] = None  # ISO format YYYY-MM-DD
    keywords: List[str] = Field(default_factory=list)
    
    authors: List[Author] = Field(default_factory=list)
    affiliations: List[Affiliation] = Field(default_factory=list)
    
    abstract: str = ""
    sections: List[Section] = Field(default_factory=list)
    figures: List[Figure] = Field(default_factory=list)
    tables: List[Table] = Field(default_factory=list)
    supplementary: List[Supplementary] = Field(default_factory=list)
```

## Supporting Models

### Section
Sections are recursive to support arbitrary nesting depths (Section -> Subsection -> Sub-subsection).

```python
class Section(BaseModel):
    title: str
    level: int  # 1=section, 2=subsection, 3=subsubsection
    content: str  # Text content before any subsections
    children: List['Section'] = Field(default_factory=list)
```

### Author & Affiliation
Maps authors to their respective affiliations using ID references.

```python
class Author(BaseModel):
    name: str
    affiliations: List[int]  # List of affiliation IDs

class Affiliation(BaseModel):
    id: int
    text: str
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
    data: List[List[str]]  # 2D list for table rows/columns
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
