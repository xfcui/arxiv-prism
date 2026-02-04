# Changelog

## 2026-02-04 - Removed Journal and Publication Date Fields

### Summary
Removed `journal` and `publication_date` fields from the Article model and both parsers to further simplify the data structure and focus on core scientific content.

### Changes Made

#### Data Model (`src/converter/models.py`)
- Removed `journal: str | None` field from `Article` class
- Removed `publication_date: str | None` field from `Article` class

#### XML Parser (`src/converter/parsers/xml_parser.py`)
- Removed journal extraction from `<journal-title>` element
- Removed publication date extraction and formatting logic
- Removed `_get_pub_date()` helper function
- Updated `Article` instantiation to exclude these fields

#### HTML Parser (`src/converter/parsers/html_parser.py`)
- Removed `_get_journal()` method
- Removed `_get_publication_date()` method
- Updated `Article` instantiation to exclude these fields

#### Markdown Formatter (`src/converter/formatters/markdown_formatter.py`)
- Simplified metadata rendering to show only DOI (if present)
- Removed journal and publication date from output

### Current Article Fields

The Article model now contains these **7 fields**:
1. `title` (str) - Article title
2. `doi` (str | None) - Digital Object Identifier
3. `abstract` (str) - Abstract text
4. `sections` (list[Section]) - Hierarchical content sections
5. `figures` (list[Figure]) - Figure metadata
6. `tables` (list[Table]) - Table data
7. `supplementary` (list[Supplementary]) - Supplementary materials

### Rationale
- **Focus on content**: Journal and publication date are publication metadata, not core scientific content
- **Simplification**: Reduces fields from 9 to 7
- **DOI sufficiency**: DOI uniquely identifies articles and can be used to retrieve all publication metadata if needed
- **Consistency**: Both parsers now extract an identical, minimal set of fields

### Verification
- ✅ All 8 output files regenerated
- ✅ No JSON files contain `journal` or `publication_date` fields
- ✅ Markdown files no longer show journal or publication date metadata
- ✅ Both parsers produce identical field sets

---

## 2026-02-04 - Parser Field Consistency Verification

### Summary
Verified that both XML (JATS/PMC) and HTML (Nature/Springer) parsers extract exactly the same fields and produce consistent output structures.

### Verification Results
All 8 output files (4 XML + 4 HTML) verified as structurally consistent:
- ✅ Both parsers extract identical field sets
- ✅ All fields have correct types matching the `Article` Pydantic model
- ✅ Nested structures (sections, figures, tables, supplementary) are consistent
- ✅ No missing or extra fields in either parser

### Fields Extracted by Both Parsers
1. **title** (str): Article title
2. **doi** (str | None): Digital Object Identifier
3. **journal** (str | None): Journal name
4. **publication_date** (str | None): Publication date in ISO format
5. **abstract** (str): Abstract text
6. **sections** (list[Section]): Hierarchical sections with title, level, content, children
7. **figures** (list[Figure]): Figures with id, label, caption
8. **tables** (list[Table]): Tables with id, label, caption, data
9. **supplementary** (list[Supplementary]): Supplementary materials with label, description

### Verification Tools Created
- `verify_parser_consistency.py`: Comprehensive structural validation
  - Validates all fields match the Article model
  - Checks nested structures recursively
  - Compares field sets between XML and HTML outputs
  - Verifies data types for all fields

---

## 2026-02-04 - Consistency Verification

### Summary
Verified and ensured complete consistency between JSON and Markdown output formats.

### Actions Taken
1. Regenerated all JSON files (both XML and HTML sources) to ensure they match the updated `Article` model without `keywords`, `authors`, and `affiliations` fields
2. Regenerated all Markdown files from both XML and HTML sources
3. Created verification scripts (`verify_json_md.py`) to automatically check that JSON and Markdown outputs are consistent
4. Confirmed that the Markdown formatter correctly renders all content from the JSON intermediate representation

### Verification Results
- All 8 file pairs (4 XML + 4 HTML) verified as consistent
- JSON can be loaded and regenerated into identical Markdown
- Title, DOI, abstract, sections, figures, tables, and supplementary materials all match between formats

---

## 2026-02-04 - Enhanced Citation Cleaning

### Summary
Improved citation removal to also clean up empty citation artifacts like `(–)`, `(, )`, `()`, and duplicate periods.

### Problem
After removing citation numbers from XML/HTML parsing, empty citation markers and punctuation artifacts were left in the text, such as:
- Empty parentheses: `(–)`, `(, )`, `()`
- Duplicate periods: `..` from cases like `. ()` → `..`
- Orphaned punctuation from citation ranges

### Solution
Enhanced the `strip_citations()` function in `text_utils.py` to:
- Remove empty citation parentheses with their surrounding spaces
- Clean up duplicate periods (`. .` → `.` and `..` → `.`)
- Remove standalone dashes and commas left from citation ranges
- Clean up multiple punctuation marks

### Files Changed
- `src/converter/text_utils.py`: Enhanced `strip_citations()` function with additional regex patterns

---

## 2026-02-04 - Bug Fix: Citation Removal in XML Parser

### Summary
Fixed incomplete text extraction where citation numbers were being concatenated instead of properly removed.

### Problem
When parsing XML files, citation references like `(1–3)` were being extracted as concatenated numbers `(123)` or incomplete text fragments, resulting in malformed output such as "26% (1345678912" instead of "26% (–)".

### Solution
Completely rewrote the `_extract_paragraph_text()` function in `xml_parser.py` to use a recursive approach that properly handles the XML tree structure. The new implementation:
- Correctly skips `<xref ref-type="bibr">` elements (citations)
- Preserves tail text that comes after skipped citations
- Properly handles nested elements
- Maintains spacing and punctuation

### Files Changed
- `src/converter/parsers/xml_parser.py`: Rewrote `_extract_paragraph_text()` function

---

## 2026-02-04 - Removed Keywords, Authors, and Affiliations

### Summary
Removed keywords, authors, and affiliations from the article processing pipeline to focus on core scientific content.

### Changes Made

#### Data Models (`src/converter/models.py`)
- Removed `Author` class
- Removed `Affiliation` class  
- Removed `keywords`, `authors`, and `affiliations` fields from `Article` class

#### Parsers
- **XML Parser** (`src/converter/parsers/xml_parser.py`)
  - Removed imports for `Author` and `Affiliation`
  - Removed `_aff_id_from_string()` helper function
  - Removed `_get_authors_affiliations()` method
  - Removed keyword extraction from `parse()` method
  
- **HTML Parser** (`src/converter/parsers/html_parser.py`)
  - Removed imports for `Author` and `Affiliation`
  - Removed `_get_keywords()` method
  - Removed `_get_authors_affiliations()` method
  - Updated `parse()` method to exclude these fields

#### Formatters
- **Markdown Formatter** (`src/converter/formatters/markdown_formatter.py`)
  - Removed rendering of authors section
  - Removed rendering of affiliations section
  - Removed rendering of keywords section
  
- **JSON Formatter** (`src/converter/formatters/json_formatter.py`)
  - No changes needed (automatically reflects model changes)

#### Documentation
- **README.md**: Updated feature list to remove mention of authors and affiliations
- **design/architecture.md**: Added note explaining exclusion of these fields
- **design/data_models.md**: Removed Author and Affiliation model documentation, added note about exclusions
- **design/parsers.md**: Updated extraction logic documentation for both parsers
- **.cursor/rules/converter-patterns.mdc**: Removed extraction patterns for keywords, authors, and affiliations; updated Article model structure

### Testing
All changes have been tested with both XML (JATS) and HTML (Nature/Springer) input files. The converter successfully processes articles without extracting or outputting keywords, authors, or affiliations.

### Rationale
This change focuses the converter on extracting the core scientific content (title, abstract, sections, figures, tables) while excluding metadata that may not be needed for certain use cases such as LLM training data or content analysis.
