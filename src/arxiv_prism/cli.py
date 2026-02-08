"""CLI for article format converter."""

import logging
import sys
from pathlib import Path

import click
from tqdm import tqdm

from arxiv_prism.formatters import JSONFormatter, MarkdownFormatter
from arxiv_prism.parsers import HTMLParser, XMLParser

logger = logging.getLogger("converter")


def _configure_logging(verbose: bool, quiet: bool) -> None:
    level = logging.DEBUG if verbose else (logging.ERROR if quiet else logging.WARNING)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


INPUT_EXTS = (".html", ".htm", ".xml", ".nxml")


def _detect_format(path: Path) -> str:
    """Return 'html' or 'xml' based on file extension."""
    suf = path.suffix.lower()
    if suf in (".html", ".htm"):
        return "html"
    if suf in (".xml", ".nxml"):
        return "xml"
    return ""


def _collect_input_files(input_dir: Path) -> list[Path]:
    """Collect all .html/.xml files under input_dir recursively."""
    return sorted(
        p for p in input_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in INPUT_EXTS
    )


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
    "--force",
    "-F",
    is_flag=True,
    help="Overwrite output file if it already exists (default: skip).",
)
def convert(
    input_file: Path,
    output: Path | None,
    output_format: str,
    input_format: str,
    force: bool,
) -> None:
    """Convert a single article file."""
    if not force and output is not None and output.exists():
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
    "--force",
    "-F",
    is_flag=True,
    help="Overwrite output files that already exist (default: skip).",
)
@click.pass_context
def batch(
    ctx: click.Context,
    input_dir: Path,
    output: Path,
    output_format: str,
    input_format: str,
    force: bool,
) -> None:
    """Convert all article files in a directory (recursive). Input: **/*.{html,xml}. Output: **/*.json or **/*.md."""
    formatter = _get_formatter(output_format)
    ext = ".json" if output_format == "json" else ".md"
    output.mkdir(parents=True, exist_ok=True)
    files = _collect_input_files(input_dir)
    if not files:
        click.echo("No .html/.xml files in directory.")
        return
    ok = 0
    skipped = 0
    quiet = ctx.parent.params.get("quiet", False) if ctx.parent else False
    iterator = tqdm(files, desc="Converting", unit="file", disable=quiet)
    for path in iterator:
        rel = path.relative_to(input_dir)
        out_path = output / rel.with_suffix(ext)
        if not force and out_path.exists():
            skipped += 1
            continue

        fmt = input_format if input_format != "auto" else _detect_format(path)
        if not fmt:
            logger.warning("Skipping %s (unknown extension).", path.name)
            continue
        try:
            parser = _get_parser(fmt)
            content = path.read_text(encoding="utf-8", errors="replace")
            article = parser.parse(content)
            out_str = formatter.format(article)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(out_str, encoding="utf-8")
            ok += 1
            if quiet:
                iterator.set_postfix_str(f"ok={ok}")
        except Exception as e:
            logger.warning("Failed %s: %s", path.name, e)
            if not quiet:
                tqdm.write(click.style(f"Failed {rel}: {e}", fg="red"))

    if not quiet:
        iterator.close()
    summary = f"Done. {ok}/{len(files)} files converted."
    if skipped:
        summary += f" {skipped} skipped (already exist)."
    click.echo(summary)


def main() -> None:
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
