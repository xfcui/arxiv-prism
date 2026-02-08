# 📄 Article Format Converter

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Turn messy scientific articles into clean, readable formats. Perfect for building LLM datasets or getting a clean Markdown version of any Nature or PubMed paper.

```
HTML/XML Article  →  arxiv-prism  →  Clean Markdown or JSON
```

## ✨ Key Features

- **✨ Nature & PubMed support** — Works with Springer HTML and PubMed Central XML out of the box
- **✨ Smart structure** — Extracts metadata, sections, and nested headings automatically
- **✨ Tables & math** — Converts tables to Markdown and keeps formulas as LaTeX
- **✨ No noise** — Strips citations and references so you can focus on content
- **✨ Batch mode** — Process entire folders in one command

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/your-repo/arxiv-prism.git
cd arxiv-prism
pip install -e .
```

### 2. Basic Usage

Run the converter with the `arxiv-prism` command:

```bash
# Single file → Markdown
arxiv-prism convert article.html -o result.md

# Folder of XMLs → JSON
arxiv-prism batch ./papers/ -o ./output/ --format json
```

Or run as a module:

```bash
python -m arxiv_prism convert article.html -o result.md
```

---

## 🛠️ Detailed Usage

Use `--help` on any command to see available flags.

| Command | Description |
| :--- | :--- |
| `convert <file>` | Convert a single article |
| `batch <dir>` | Convert all files in a directory |

**Common flags:**

| Flag | What it does |
| :--- | :--- |
| `-o, --output` | Output file or directory |
| `-f, --format` | `markdown` or `json` (default: `json` for single, `markdown` for batch) |
| `-F, --force` | Overwrite output if it already exists (default: skip) |
| `--input-format` | Force `html`, `xml`, or `auto` (default: `auto`) |
| `-v, --verbose` | Show detailed progress |
| `-q, --quiet` | Suppress all non-error output |

---

## 📂 Supported Sources

| Source | Format | Example |
| :--- | :--- | :--- |
| **Nature / Springer** | HTML | Full article pages from nature.com |
| **PubMed Central** | XML | JATS standard files from PMC |

---

## 📖 Learn More

Check out the [Design Docs](./design/architecture.md) for architecture details and data models.

## 🤝 Contributing

Contributions welcome! Feel free to open an issue or submit a PR.

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
