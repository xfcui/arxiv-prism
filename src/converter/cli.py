"""CLI for article format converter."""

import logging
import sys
from pathlib import Path

import click

from converter.formatters import JSONFormatter, MarkdownFormatter
from converter.parsers import HTMLParser, XMLParser

logger = logging.getLogger("converter")


def _configure_logging(verbose: bool, quiet: bool) -> None:
    level = logging.DEBUG if verbose else (logging.ERROR if quiet else logging.WARNING)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def _detect_format(path: Path) -> str:
    """Return 'html' or 'xml' based on file extension."""
    suf = path.suffix.lower()
    if suf in (".html", ".htm"):
        return "html"
    if suf in (".xml", ".nxml"):
        return "xml"
    return ""


def _get_parser(fmt: str):
    if fmt == "html":
        return HTMLParser()
    if fmt == "xml":
        return XMLParser()
    raise click.UsageError(f"Unknown input format: {fmt}. Use .html or .xml.")


def _get_formatter(fmt: str):
    if fmt == "json":
        return JSONFormatter()
    if fmt in ("markdown", "md"):
        return MarkdownFormatter()
    raise click.UsageError(f"Unknown output format: {fmt}. Use json or markdown.")


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """Convert articles from HTML/XML to JSON or Markdown."""
    _configure_logging(verbose, quiet)
    ctx.ensure_object(dict)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: stdout).",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format.",
)
@click.option(
    "--input-format",
    type=click.Choice(["html", "xml", "auto"]),
    default="auto",
    help="Input format (default: auto from extension).",
)
@click.option(
    "--skip-exist",
    is_flag=True,
    help="Skip processing if output file already exists.",
)
def convert(
    input_file: Path,
    output: Path | None,
    output_format: str,
    input_format: str,
    skip_exist: bool,
) -> None:
    """Convert a single article file."""
    if skip_exist and output is not None and output.exists():
        click.echo(f"Skipping {input_file.name} (output exists: {output})")
        return
    
    fmt = input_format
    if fmt == "auto":
        fmt = _detect_format(input_file)
        if not fmt:
            raise click.BadParameter(
                "Could not detect input format from extension. Use --input-format html|xml."
            )
    parser = _get_parser(fmt)
    formatter = _get_formatter(output_format)
    try:
        content = input_file.read_text(encoding="utf-8", errors="replace")
        article = parser.parse(content)
        out_str = formatter.format(article)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(out_str, encoding="utf-8")
            if not logger.isEnabledFor(logging.ERROR):
                click.echo(f"Wrote {output}")
        else:
            click.echo(out_str)
    except Exception as e:
        logger.exception("Conversion failed")
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output directory.",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "markdown"]),
    default="markdown",
    help="Output format.",
)
@click.option(
    "--input-format",
    type=click.Choice(["html", "xml", "auto"]),
    default="auto",
    help="Input format (default: auto from extension).",
)
@click.option(
    "--skip-exist",
    is_flag=True,
    help="Skip processing if output file already exists.",
)
def batch(
    input_dir: Path,
    output: Path,
    output_format: str,
    input_format: str,
    skip_exist: bool,
) -> None:
    """Convert all article files in a directory."""
    formatter = _get_formatter(output_format)
    ext = ".json" if output_format == "json" else ".md"
    output.mkdir(parents=True, exist_ok=True)
    files = list(input_dir.iterdir())
    if not files:
        click.echo("No files in directory.")
        return
    ok = 0
    skipped = 0
    for path in sorted(files):
        if not path.is_file():
            continue
        
        out_path = output / (path.stem + ext)
        if skip_exist and out_path.exists():
            click.echo(f"Skipping {path.name} (output exists: {out_path.name})")
            skipped += 1
            continue
        
        fmt = input_format
        if fmt == "auto":
            fmt = _detect_format(path)
            if not fmt:
                logger.warning("Skipping %s (unknown extension).", path.name)
                continue
        try:
            parser = _get_parser(fmt)
            content = path.read_text(encoding="utf-8", errors="replace")
            article = parser.parse(content)
            out_str = formatter.format(article)
            out_path.write_text(out_str, encoding="utf-8")
            ok += 1
            click.echo(f"Converted {path.name} -> {out_path.name}")
        except Exception as e:
            logger.warning("Failed %s: %s", path.name, e)
            click.secho(f"Failed {path.name}: {e}", fg="red")
    
    summary = f"Done. {ok}/{len(files)} files converted."
    if skipped:
        summary += f" {skipped} skipped (already exist)."
    click.echo(summary)


def main() -> None:
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
