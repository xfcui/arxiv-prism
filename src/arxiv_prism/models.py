"""Pydantic models for the article intermediate representation."""

from pydantic import BaseModel, Field


class Author(BaseModel):
    """Author metadata."""

    name: str
    authtype: str = "Author"


class Section(BaseModel):
    """Recursive section (section, subsection, subsubsection)."""

    title: str
    level: int = Field(ge=1, le=10, description="1=section, 2=subsection, ... 10=deepest")
    content: str = ""
    sections: list["Section"] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


Section.model_rebuild()


class Figure(BaseModel):
    """Figure metadata (image omitted in output)."""

    id: str
    label: str
    caption: str


class Table(BaseModel):
    """Table with caption and row/column data."""

    id: str
    label: str
    caption: str
    data: list[list[str]] = Field(default_factory=list)


class Supplementary(BaseModel):
    """Supplementary material entry."""

    label: str
    description: str


class Article(BaseModel):
    """Full article intermediate representation."""

    title: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    pubdate: str | None = None
    epubdate: str = ""
    printpubdate: str = ""
    authors: list[Author] = Field(default_factory=list)
    volume: str = ""
    issue: str = ""
    pages: str = ""

    abstract: str = ""
    sections: list[Section] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    supplementary: list[Supplementary] = Field(default_factory=list)

    model_config = {"extra": "forbid"}
