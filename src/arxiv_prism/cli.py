"""CLI for article format converter."""

import json
import logging
import sys
from pathlib import Path

import click
from tqdm import tqdm

from arxiv_prism.formatters import JSONFormatter, MarkdownFormatter
from arxiv_prism.parsers import HTMLParser, XMLParser

logger = logging.getLogger("converter")


_SPRINGER_JOURNAL_MAP: dict[str, tuple[str, str]] = {
    "Nature": ("Nature", "Nature"),
    "Nature_Immunology": ("Nat Immunol", "Nature immunology"),
    "Nature_Biotechnology": ("Nat Biotechnol", "Nature biotechnology"),
    "Nature_Computational_Science": ("Nat Comput Sci", "Nature computational science"),
    "Nature_Machine_Intelligence": ("Nat Mach Intell", "Nature machine intelligence"),
}

_ELSEVIER_JOURNAL_MAP: dict[str, tuple[str, str]] = {
    "Cell": ("Cell", "Cell"),
    "Cell_Immunity": ("Immunity", "Immunity"),
}

_MONTH_TO_NUM: dict[str, str] = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}


def _pubdate_to_sortdate(pubdate: str) -> str:
    """Convert 'YYYY Mon D' pubdate to 'YYYY/MM/DD 00:00' sortdate matching NCBI format."""
    parts = pubdate.strip().split()
    if len(parts) < 2:
        return ""
    year = parts[0]
    month = _MONTH_TO_NUM.get(parts[1], "00")
    day = parts[2].zfill(2) if len(parts) > 2 else "01"
    return f"{year}/{month}/{day} 00:00"


def _infer_journal(input_path: Path) -> tuple[str, str]:
    """Infer source abbreviation and full journal name from the file path."""
    journal_dir = input_path.parent.name
    return (
        _SPRINGER_JOURNAL_MAP.get(journal_dir)
        or _ELSEVIER_JOURNAL_MAP.get(journal_dir)
        or ("", "")
    )


def _save_meta_json(article, input_path: Path, force: bool) -> None:
    """Save article metadata to *_meta.json if it doesn't exist or force is True."""
    meta_path = input_path.parent / f"{input_path.stem}_meta.json"
    if not force and meta_path.exists():
        return

    pubdate = article.pubdate or ""
    source, fulljournalname = _infer_journal(input_path)

    # Map Article model to the expected meta.json format
    meta = {
        "uid": article.pmcid.replace("PMC", "") if article.pmcid else "",
        "pubdate": pubdate,
        "epubdate": article.epubdate,
        "printpubdate": article.printpubdate,
        "source": source,
        "authors": [
            {"name": a.name, "authtype": a.authtype}
            for a in article.authors
        ],
        "title": article.title,
        "volume": article.volume,
        "issue": article.issue,
        "pages": article.pages,
        "articleids": [],
        "fulljournalname": fulljournalname,
        "sortdate": _pubdate_to_sortdate(pubdate) if pubdate else "",
        "pmclivedate": ""
    }

    # Match NCBI articleids order: pmid → pmcid → doi
    if article.pmid:
        meta["articleids"].append({"idtype": "pmid", "value": article.pmid})
    if article.pmcid:
        meta["articleids"].append({"idtype": "pmcid", "value": article.pmcid})
    if article.doi:
        meta["articleids"].append({"idtype": "doi", "value": article.doi})

    try:
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to write metadata for {input_path.name}: {e}")


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
    meta_path = input_file.parent / f"{input_file.stem}_meta.json"
    if not force and output is not None and output.exists() and meta_path.exists():
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
        
        # Generate metadata file
        _save_meta_json(article, input_file, force)
        
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
@click.argument(
    "input_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="articles",
    required=False,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory (default: same as input_dir).",
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
    output: Path | None,
    output_format: str,
    input_format: str,
    force: bool,
) -> None:
    """Convert article files in a directory. Default: articles/**/*.{html,xml} → articles/**/*.md."""
    output = output or input_dir
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
        meta_path = path.parent / f"{path.stem}_meta.json"
        
        if not force and out_path.exists() and meta_path.exists():
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
            
            # Generate metadata file
            _save_meta_json(article, path, force)
            
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


@cli.command()
@click.option(
    "--data-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="data",
    help="Data directory to watch/process (default: data).",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "markdown"]),
    default="markdown",
    help="Output format (default: markdown).",
)
@click.option(
    "--force",
    "-F",
    is_flag=True,
    help="Overwrite output files that already exist (default: skip).",
)
@click.pass_context
def auto(
    ctx: click.Context,
    data_dir: Path,
    output_format: str,
    force: bool,
) -> None:
    """Automatically convert all .xml/.html files in data/ to .md.
    
    Equivalent to: batch data/ --output data/ --format markdown
    """
    ctx.invoke(
        batch,
        input_dir=data_dir,
        output=data_dir,
        output_format=output_format,
        input_format="auto",
        force=force,
    )


def main() -> None:
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
