"""
Provide some basic tools for manipulating text.
"""

import textwrap

import pyperclip


def dedent(text: str) -> str:
    """
    Dedents a paragraph after removing leading and trailing whitespace.
    """
    return textwrap.dedent(text).strip()


def unwrap(text: str) -> str:
    """
    Unwraps a paragraph of text into a single line.

    The text may be indented.
    """
    return " ".join(dedent(text).split("\n"))


def conjoin(*items: str, join_str: str = "\n") -> str:
    """
    Joins strings supplied as args.

    Helper that wraps ``str.join()`` without having to pack strings in an iterable.
    """
    return join_str.join(items)


def dedent_all(*texts: str, join_str: str = "\n") -> str:
    """
    Dedents each blob supplied as an argument and then joins them.
    """
    return conjoin(*(dedent(b) for b in texts), join_str=join_str)


def indent(text: str, prefix: str = "    ", **kwargs) -> str:
    """
    Simple wrapper for the textwrap.indent() method but includes a default prefix.
    """
    return textwrap.indent(text, prefix=prefix, **kwargs)


def copy_to_clipboard(text: str) -> bool:
    """
    Copy the provided text to the clipboard.

    If the clipboard is not available, return False. Otherwise, return True.
    """
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False
