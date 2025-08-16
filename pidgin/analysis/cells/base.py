"""Base class for notebook cell creation."""

from typing import Any, Dict

try:
    import nbformat
    from nbformat.v4 import new_code_cell, new_markdown_cell

    NBFORMAT_AVAILABLE = True
except ImportError:
    NBFORMAT_AVAILABLE = False
    nbformat = None
    new_code_cell = None
    new_markdown_cell = None


class CellBase:
    """Base class with common cell creation utilities."""

    def _make_markdown_cell(self, content: str) -> Dict[str, Any]:
        """Create a markdown cell, handling missing nbformat."""
        if new_markdown_cell is None:
            return {"cell_type": "markdown", "source": content}
        return new_markdown_cell(content)

    def _make_code_cell(self, code: str) -> Dict[str, Any]:
        """Create a code cell, handling missing nbformat."""
        if new_code_cell is None:
            return {"cell_type": "code", "source": code}
        return new_code_cell(code)
