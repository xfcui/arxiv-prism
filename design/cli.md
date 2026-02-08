# CLI Design

The converter provides a command-line interface via the `arxiv-prism` command, built with `click`.

## Commands

### `convert`
Converts a single file.

```bash
arxiv-prism convert <input_file> [OPTIONS]
```

Or via module:

```bash
python -m arxiv_prism convert <input_file> [OPTIONS]
```

**Options:**
- `-o, --output`: Path to output file (default: stdout).
- `-f, --format`: Output format (`json` or `markdown`). Default: `json`.
- `--input-format`: Input format (`html`, `xml`, or `auto`). Default: `auto`.
- `-F, --force`: Overwrite output if it already exists (default: skip when output exists).
- `-v, --verbose`: Increase logging verbosity (DEBUG).
- `-q, --quiet`: Suppress non-error output (ERROR only).

### `batch`
Converts all files in a directory.

```bash
arxiv-prism batch <input_dir> --output <output_dir> [OPTIONS]
```

**Options:**
- `-o, --output`: Directory to save converted files (required).
- `-f, --format`: Output format (`json` or `markdown`). Default: `markdown`.
- `--input-format`: Input format (`html`, `xml`, or `auto`). Default: `auto`.
- `-F, --force`: Overwrite output files that already exist (default: skip when output exists).
- `-v, --verbose`: Increase logging verbosity.
- `-q, --quiet`: Suppress non-error output (also disables progress bar).

Batch discovers all `*.html`, `*.htm`, `*.xml`, `*.nxml` under the input directory recursively and shows a tqdm progress bar unless `--quiet` is set.

## Error Handling
- **Missing Required Fields**: Log a warning and use placeholders (e.g., "Unknown Title").
- **Parsing Errors**: Log the error with file context and skip the file in batch mode.
- **Validation Errors**: Pydantic will raise errors for structural issues, which are caught and logged.

## Logging
Uses the standard Python `logging` module. Level is set from flags:
- `-v` / `--verbose`: `DEBUG`.
- Default: `WARNING` (missing elements, non-critical parsing issues).
- `-q` / `--quiet`: `ERROR` only (critical failures).
