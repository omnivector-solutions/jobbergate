"""
Provide some helper tools for encoding and decoding strings to and from base64.
"""

from base64 import b64decode, b64encode


def decode(text: str) -> str:
    """
    Base 64 decode a string.
    """
    return b64decode(text.encode('utf-8')).decode('utf-8')


def encode(text: str) -> str:
    """
    Base 64 encode a string.
    """
    return b64encode(text.encode('utf-8')).decode('utf-8')
