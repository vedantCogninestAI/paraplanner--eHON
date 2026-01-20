"""Utility functions module"""
from .xml_helpers import escape_xml, smart_sentence_split
from .text_formatters import (
    format_as_bullets,
    format_as_newlines,
    format_as_newlines_with_bold,
    format_vulnerability_soft_notes
)

__all__ = [
    "escape_xml",
    "smart_sentence_split",
    "format_as_bullets",
    "format_as_newlines",
    "format_as_newlines_with_bold",
    "format_vulnerability_soft_notes"
]