# tiny_iana_media_type_registry

A small, dependency-free lookup and validation table for IANA media types with bundled file-extension mappings.

```python
from tiny_iana_media_type_registry import MediaTypeRegistry, UnknownMediaTypeError

registry = MediaTypeRegistry()

registry.is_valid("text/html")              # True
registry.is_valid("text/html; charset=utf-8")  # True
registry.is_valid("text/nope")              # False

media_type = registry.lookup("application/json")
print(media_type.full_type)                 # application/json
print(registry.extensions_for("text/html")) # ('html', 'htm')

print(registry.media_types_for_extension("png"))  # ('image/png',)
try:
    registry.media_types_for_extension("nope")
except UnknownMediaTypeError:
    pass
```

## Why this exists

Most projects that need to validate a MIME type either pull in a large HTTP library or hard-code a handful of strings. This package sits in between: it bundles a curated subset of the IANA registry and the file extensions that go with it, so you can answer questions like "is this a real media type?" and "what extensions does it use?" without a network call or a heavy dependency.

The trade-off is coverage. Only the media types that appear in ordinary web servers, build tools, and configuration files are included. If you need every registered type, use the full IANA registry; if you need the common ones and a stable API, this is enough.

## API

The package exports:

- `MediaType` — a frozen dataclass with `type`, `subtype`, `parameters`, and a `full_type` property. `MediaType.parse(text)` raises `InvalidMediaTypeError` on malformed input.
- `MediaTypeRegistry` — the lookup table. Methods: `is_valid(media_type)`, `lookup(media_type)`, `extensions_for(media_type)`, `media_types_for_extension(extension)`, `all_media_types_for_extension(extension)`, `types()`, and `extensions()`. It also supports `in`.
- `InvalidMediaTypeError` — raised when a string is not syntactically a media type.
- `UnknownMediaTypeError` — raised when a well-formed media type or extension is not in the registry.
- `AmbiguousExtensionError` — raised by `media_types_for_extension` when an extension maps to more than one media type.

## The awkward edge

Some extensions are genuinely ambiguous. `.ts` is both `text/typescript` and `video/mp2t`, and `.js` is both `application/javascript` and `text/javascript`. The registry does not guess: `media_types_for_extension("ts")` raises `AmbiguousExtensionError`. Use `all_media_types_for_extension("ts")` to get the full tuple and decide for yourself. This is the one place where the library refuses to be clever, because any choice would be wrong for half the callers.

Media types are matched case-insensitively and normalised to lower case. Parameters are parsed and preserved but are not part of the registry key, because the registry does not define a canonical parameter set for most types.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

