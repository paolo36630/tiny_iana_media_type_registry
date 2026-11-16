"""Core registry implementation for tiny_iana_media_type_registry.

This module bundles a small, hand-curated subset of the IANA Media Type
Registry together with file extension mappings. It is intentionally small:
the goal is to validate and look up the media types that appear in ordinary
config files and HTTP headers, not to be a complete mirror of the registry.

Design decisions worth calling out:

* Media types are compared case-insensitively and normalised to lower case.
  The IANA registry treats type/subtype as case-insensitive, so ``Text/HTML``
  and ``text/html`` refer to the same entry.
* Parameters (``; charset=utf-8``) are parsed and preserved, but the registry
  key is only ``type/subtype``. Parameter matching is not attempted because
  the registry does not define a canonical parameter set for most types.
* File extensions are stored without a leading dot and compared
  case-insensitively. A single extension may map to several media types
  (for example ``.ts`` is both ``text/typescript`` and
  ``video/mp2t``); this is reported as an ambiguity rather than silently
  picking one.

No third-party dependencies are used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple


class MediaTypeError(ValueError):
    """Base class for errors raised by this package."""


class InvalidMediaTypeError(MediaTypeError):
    """Raised when a string is not a syntactically valid media type."""


class UnknownMediaTypeError(MediaTypeError):
    """Raised when a well-formed media type is not present in the registry."""


class AmbiguousExtensionError(MediaTypeError):
    """Raised when an extension maps to more than one media type."""


# RFC 6838 restricts type and subtype to a limited token set. We use a
# slightly permissive pattern that still rejects whitespace, slashes, and
# control characters. The registry only contains lower-case entries, so we
# normalise before matching.
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$")

# A parameter is ``; name=value`` where value may be a token or a quoted
# string. We only need to find the first ``;`` that is not inside a quoted
# string, so a small scanner is clearer than a full parser.
_PARAM_SPLIT_RE = re.compile(r";(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")


@dataclass(frozen=True)
class MediaType:
    """A parsed media type.

    Attributes:
        type: The primary type, lower-cased (for example ``"text"``).
        subtype: The subtype, lower-cased (for example ``"html"``).
        parameters: A tuple of ``(name, value)`` pairs in the order they
            appeared. Names are lower-cased; values keep their original case.
    """

    type: str
    subtype: str
    parameters: Tuple[Tuple[str, str], ...] = ()

    @property
    def full_type(self) -> str:
        """Return ``type/subtype`` without parameters."""
        return f"{self.type}/{self.subtype}"

    def __str__(self) -> str:
        """Render the media type including parameters."""
        if not self.parameters:
            return self.full_type
        rendered = "; ".join(f"{k}={v}" for k, v in self.parameters)
        return f"{self.full_type}; {rendered}"

    @classmethod
    def parse(cls, value: str) -> "MediaType":
        """Parse a media type string.

        Raises InvalidMediaTypeError if the value is not a syntactically
        valid media type. This is deliberately strict: it is better to
        reject ``text/`` than to guess what the caller meant.
        """
        if not isinstance(value, str):
            raise InvalidMediaTypeError(
                f"media type must be a string, got {type(value).__name__}"
            )
        raw = value.strip()
        if not raw:
            raise InvalidMediaTypeError("media type is empty")

        # Split off parameters. The first segment is the type/subtype.
        parts = _PARAM_SPLIT_RE.split(raw)
        essence = parts[0].strip()
        if "/" not in essence:
            raise InvalidMediaTypeError(
                f"media type {value!r} is missing a '/' separator"
            )
        type_part, subtype_part = essence.split("/", 1)
        type_part = type_part.strip().lower()
        subtype_part = subtype_part.strip().lower()
        if not _TOKEN_RE.match(type_part):
            raise InvalidMediaTypeError(f"invalid type token: {type_part!r}")
        if not _TOKEN_RE.match(subtype_part):
            raise InvalidMediaTypeError(f"invalid subtype token: {subtype_part!r}")

        parameters: List[Tuple[str, str]] = []
        for chunk in parts[1:]:
            chunk = chunk.strip()
            if not chunk:
                raise InvalidMediaTypeError(
                    f"empty parameter in media type {value!r}"
                )
            if "=" not in chunk:
                raise InvalidMediaTypeError(
                    f"parameter {chunk!r} is missing '='"
                )
            name, param_value = chunk.split("=", 1)
            name = name.strip().lower()
            param_value = param_value.strip()
            if not name:
                raise InvalidMediaTypeError(
                    f"empty parameter name in media type {value!r}"
                )
            if param_value.startswith('"') and param_value.endswith('"') and len(param_value) >= 2:
                param_value = param_value[1:-1]
            parameters.append((name, param_value))

        return cls(type=type_part, subtype=subtype_part, parameters=tuple(parameters))


# The bundled registry. Each entry maps ``type/subtype`` to a tuple of
# extensions (without dots). The data is intentionally small but covers the
# media types that show up in web servers, build tools, and configuration
# files.
_REGISTRY_DATA: Dict[str, Tuple[str, ...]] = {
    "application/atom+xml": ("atom",),
    "application/ecmascript": ("es",),
    "application/epub+zip": ("epub",),
    "application/gzip": ("gz",),
    "application/javascript": ("js", "mjs"),
    "application/json": ("json",),
    "application/ld+json": ("jsonld",),
    "application/msword": ("doc",),
    "application/octet-stream": ("bin",),
    "application/ogg": ("ogx",),
    "application/pdf": ("pdf",),
    "application/postscript": ("ps",),
    "application/rss+xml": ("rss",),
    "application/rtf": ("rtf",),
    "application/vnd.ms-excel": ("xls",),
    "application/vnd.ms-powerpoint": ("ppt",),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ("pptx",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ("xlsx",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ("docx",),
    "application/wasm": ("wasm",),
    "application/x-7z-compressed": ("7z",),
    "application/x-bzip2": ("bz2",),
    "application/x-httpd-php": ("php",),
    "application/x-tar": ("tar",),
    "application/xhtml+xml": ("xhtml",),
    "application/xml": ("xml",),
    "application/zip": ("zip",),
    "audio/aac": ("aac",),
    "audio/flac": ("flac",),
    "audio/mpeg": ("mp3",),
    "audio/ogg": ("oga", "ogg"),
    "audio/wav": ("wav",),
    "audio/webm": ("weba",),
    "font/otf": ("otf",),
    "font/ttf": ("ttf",),
    "font/woff": ("woff",),
    "font/woff2": ("woff2",),
    "image/avif": ("avif",),
    "image/bmp": ("bmp",),
    "image/gif": ("gif",),
    "image/jpeg": ("jpg", "jpeg"),
    "image/png": ("png",),
    "image/svg+xml": ("svg",),
    "image/tiff": ("tif", "tiff"),
    "image/webp": ("webp",),
    "image/x-icon": ("ico",),
    "message/http": (),
    "model/gltf+json": ("gltf",),
    "model/gltf-binary": ("glb",),
    "model/obj": ("obj",),
    "model/stl": ("stl",),
    "text/calendar": ("ics",),
    "text/css": ("css",),
    "text/csv": ("csv",),
    "text/html": ("html", "htm"),
    "text/javascript": ("js", "mjs"),
    "text/markdown": ("md", "markdown"),
    "text/plain": ("txt", "text"),
    "text/tab-separated-values": ("tsv",),
    "text/typescript": ("ts",),
    "text/vcard": ("vcf",),
    "text/xml": ("xml",),
    "video/mp2t": ("ts",),
    "video/mp4": ("mp4",),
    "video/mpeg": ("mpeg", "mpg"),
    "video/ogg": ("ogv",),
    "video/quicktime": ("mov",),
    "video/webm": ("webm",),
    "video/x-msvideo": ("avi",),
}


def _build_extension_index(
    data: Mapping[str, Sequence[str]]
) -> Dict[str, FrozenSet[str]]:
    """Invert the registry into an extension -> media types mapping.

    Extensions are lower-cased and stored without a leading dot. The result
    is a mapping from extension to a frozenset of media types, which makes
    ambiguity detection a simple length check.
    """
    index: Dict[str, set] = {}
    for media_type, extensions in data.items():
        for ext in extensions:
            normalised = ext.lower().lstrip(".")
            if not normalised:
                continue
            index.setdefault(normalised, set()).add(media_type)
    return {ext: frozenset(types) for ext, types in index.items()}


@dataclass
class MediaTypeRegistry:
    """A lookup table for IANA media types and their file extensions.

    The registry is immutable from the caller's point of view: the bundled
    data is copied into internal dictionaries at construction time. This
    avoids accidental mutation of module-level state.
    """

    _by_type: Dict[str, Tuple[str, ...]] = field(init=False, repr=False)
    _by_extension: Dict[str, FrozenSet[str]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._by_type = {k.lower(): tuple(v) for k, v in _REGISTRY_DATA.items()}
        self._by_extension = _build_extension_index(self._by_type)

    def __contains__(self, media_type: object) -> bool:
        """Return True if the media type (or a MediaType) is registered."""
        if isinstance(media_type, MediaType):
            key = media_type.full_type
        elif isinstance(media_type, str):
            try:
                key = MediaType.parse(media_type).full_type
            except InvalidMediaTypeError:
                return False
        else:
            return False
        return key in self._by_type

    def is_valid(self, media_type: str) -> bool:
        """Return True if ``media_type`` is syntactically valid and known.

        Invalid syntax returns False rather than raising, because callers
        validating untrusted input usually want a boolean.
        """
        try:
            parsed = MediaType.parse(media_type)
        except InvalidMediaTypeError:
            return False
        return parsed.full_type in self._by_type

    def lookup(self, media_type: str) -> MediaType:
        """Return the parsed MediaType for a registered media type.

        Raises InvalidMediaTypeError for malformed input and
        UnknownMediaTypeError for well-formed but unregistered types.
        """
        parsed = MediaType.parse(media_type)
        if parsed.full_type not in self._by_type:
            raise UnknownMediaTypeError(
                f"media type {parsed.full_type!r} is not in the registry"
            )
        return parsed

    def extensions_for(self, media_type: str) -> Tuple[str, ...]:
        """Return the known file extensions for a media type.

        Extensions are returned without a leading dot, in the order they
        appear in the bundled data. An empty tuple means the media type is
        registered but has no extension mapping (for example
        ``message/http``).

        Raises InvalidMediaTypeError or UnknownMediaTypeError as in
        :meth:`lookup`.
        """
        parsed = self.lookup(media_type)
        return self._by_type[parsed.full_type]

    def media_types_for_extension(self, extension: str) -> Tuple[str, ...]:
        """Return all media types registered for a file extension.

        The extension may be given with or without a leading dot and is
        matched case-insensitively. If the extension maps to more than one
        media type, an AmbiguousExtensionError is raised rather than
        guessing. Callers that want to handle ambiguity themselves should
        use :meth:`all_media_types_for_extension`.
        """
        matches = self.all_media_types_for_extension(extension)
        if not matches:
            raise UnknownMediaTypeError(
                f"no media type registered for extension {extension!r}"
            )
        if len(matches) > 1:
            raise AmbiguousExtensionError(
                f"extension {extension!r} maps to multiple media types: "
                + ", ".join(matches)
            )
        return matches

    def all_media_types_for_extension(self, extension: str) -> Tuple[str, ...]:
        """Return every media type registered for an extension.

        Returns an empty tuple when the extension is unknown. This is the
        non-raising counterpart to :meth:`media_types_for_extension`.
        """
        if not isinstance(extension, str):
            raise InvalidMediaTypeError(
                f"extension must be a string, got {type(extension).__name__}"
            )
        normalised = extension.lower().lstrip(".")
        if not normalised:
            return ()
        return tuple(sorted(self._by_extension.get(normalised, frozenset())))

    def types(self) -> Tuple[str, ...]:
        """Return all registered media types in sorted order."""
        return tuple(sorted(self._by_type))

    def extensions(self) -> Tuple[str, ...]:
        """Return all known extensions in sorted order."""
        return tuple(sorted(self._by_extension))
