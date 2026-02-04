# 📄 Article Format Converter

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Transform complex scientific articles into clean, readable formats. Whether you're building a dataset for LLMs or just need a clean Markdown version of a Nature paper, this tool has you covered.

## ✨ Key Features

- **Multi-Source Support**: Seamlessly handles Nature/Springer HTML and PubMed Central (JATS) XML.
- **Smart Extraction**: Captures metadata and recursive section hierarchies from scientific articles.
- **Rich Elements**: Converts complex tables to Markdown and preserves mathematical formulas as LaTeX.
- **Clean Output**: Automatically strips citations and reference lists for a focused reading experience.
- **Batch Processing**: Convert entire directories of research papers in one command.

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/your-repo/article-converter.git
cd article-converter
pip install -r requirements.txt
```

### 2. Basic Usage

Convert a single article to Markdown:

```bash
python -m converter convert article.html -o result.md
```

Convert a folder of XML files to JSON:

```bash
python -m converter batch ./xml_files/ -o ./output_json/ --format json
```

---

## 🛠️ Detailed Usage

The CLI is designed to be intuitive. Use `--help` on any command to see all options.

### Single File Conversion
```bash
python -m converter convert <input_path> [OPTIONS]
```
- `-o, --output`: Specify output filename.
- `-f, --format`: Choose `markdown` or `json`. Default: `json`.
- `--input-format`: Choose `html`, `xml`, or `auto`. Default: `auto`.
- `-v, --verbose`: See what's happening under the hood.
- `-q, --quiet`: Suppress non-error output.

### Batch Processing
```bash
python -m converter batch <directory_path> --output <output_dir> [OPTIONS]
```
- `-o, --output`: Where to save the results.
- `-f, --format`: Choose `markdown` or `json`. Default: `markdown`.
- `--input-format`: Choose `html`, `xml`, or `auto`. Default: `auto`.
- `-v, --verbose`: See what's happening under the hood.
- `-q, --quiet`: Suppress non-error output.

---

## 📂 Supported Formats

| Source | Format | Description |
| :--- | :--- | :--- |
| **Nature / Springer** | HTML | Full article pages from nature.com or springer.com |
| **PubMed Central** | XML | JATS (Journal Article Tag Suite) standard files |

---

## 📖 Documentation

For a deeper dive into the system architecture and data models, check out our [Design Docs](./design/architecture.md).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
