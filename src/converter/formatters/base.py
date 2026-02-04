"""Abstract base formatter for article output."""

from abc import ABC, abstractmethod

from converter.models import Article


class BaseFormatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def format(self, article: Article) -> str:
        """Format an Article to output string (JSON or Markdown).

        Args:
            article: Parsed article model.

        Returns:
            Formatted string.
        """
        pass
