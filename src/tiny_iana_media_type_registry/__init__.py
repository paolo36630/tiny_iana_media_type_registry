"""Public API for tiny_iana_media_type_registry.

Only the names listed in __all__ are part of the supported interface.
"""

from .core import (
    MediaType,
    MediaTypeRegistry,
    UnknownMediaTypeError,
    InvalidMediaTypeError,
    AmbiguousExtensionError,
)

__all__ = [
    "MediaType",
    "MediaTypeRegistry",
    "UnknownMediaTypeError",
    "InvalidMediaTypeError",
    "AmbiguousExtensionError",
]
