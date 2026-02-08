"""JSON formatter for article output."""

import json

from arxiv_prism.models import Article
from arxiv_prism.formatters.base import BaseFormatter


class JSONFormatter(BaseFormatter):
    """Format Article as JSON string."""

    def format(self, article: Article) -> str:
        """Serialize article to JSON without indentation."""
        return json.dumps(
            article.model_dump(mode="json"),
            ensure_ascii=False,
        )
