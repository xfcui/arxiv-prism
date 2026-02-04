# CLI Design

The converter provides a command-line interface built with `click`.

## Commands

### `convert`
Converts a single file.

```bash
python -m converter convert <input_file> [OPTIONS]
```

**Options:**
- `-o, --output`: Path to output file.
- `-f, --format`: Output format (`json` or `markdown`). Auto-detected if omitted.
- `-v, --verbose`: Increase logging verbosity.

### `batch`
Converts all files in a directory.

```bash
python -m converter batch <input_dir> [OPTIONS]
```

**Options:**
- `-o, --output-dir`: Directory to save converted files.
- `-f, --format`: Output format.
- `--recursive`: Search subdirectories for input files.

## Error Handling
- **Missing Required Fields**: Log a warning and use placeholders (e.g., "Unknown Title").
- **Parsing Errors**: Log the error with file context and skip the file in batch mode.
- **Validation Errors**: Pydantic will raise errors for structural issues, which are caught and logged.

## Logging
Uses the standard Python `logging` module.
- `INFO`: General progress.
- `WARNING`: Missing elements or non-critical parsing issues.
- `ERROR`: Critical failures (file not found, invalid format).
