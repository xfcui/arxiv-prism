"""Abstract base parser for article formats."""

from abc import ABC, abstractmethod

from arxiv_prism.models import Article


class BaseParser(ABC):
    """Abstract base class for article parsers."""

    @abstractmethod
    def parse(self, content: str) -> Article:
        """Parse input content into an Article intermediate representation.

        Args:
            content: Raw HTML or XML string.

        Returns:
            Article model instance.
        """
        pass
