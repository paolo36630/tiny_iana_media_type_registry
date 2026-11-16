import unittest

from tiny_iana_media_type_registry import (
    AmbiguousExtensionError,
    InvalidMediaTypeError,
    MediaType,
    MediaTypeRegistry,
    UnknownMediaTypeError,
)


class MediaTypeParseTests(unittest.TestCase):
    def test_parse_simple(self):
        mt = MediaType.parse("text/html")
        self.assertEqual(mt.type, "text")
        self.assertEqual(mt.subtype, "html")
        self.assertEqual(mt.parameters, ())
        self.assertEqual(str(mt), "text/html")

    def test_parse_normalises_case(self):
        mt = MediaType.parse("TEXT/HTML")
        self.assertEqual(mt.full_type, "text/html")

    def test_parse_parameters(self):
        mt = MediaType.parse("text/html; charset=UTF-8; boundary=abc")
        self.assertEqual(mt.parameters, (("charset", "UTF-8"), ("boundary", "abc")))
        self.assertEqual(str(mt), "text/html; charset=UTF-8; boundary=abc")

    def test_parse_quoted_parameter(self):
        mt = MediaType.parse('text/plain; title="a; b"')
        self.assertEqual(mt.parameters, (("title", "a; b"),))

    def test_parse_rejects_missing_slash(self):
        with self.assertRaises(InvalidMediaTypeError):
            MediaType.parse("text")

    def test_parse_rejects_empty(self):
        with self.assertRaises(InvalidMediaTypeError):
            MediaType.parse("")

    def test_parse_rejects_bad_token(self):
        with self.assertRaises(InvalidMediaTypeError):
            MediaType.parse("text/")
        with self.assertRaises(InvalidMediaTypeError):
            MediaType.parse("text/ht ml")

    def test_parse_rejects_non_string(self):
        with self.assertRaises(InvalidMediaTypeError):
            MediaType.parse(123)  # type: ignore[arg-type]

    def test_parse_rejects_empty_parameter(self):
        with self.assertRaises(InvalidMediaTypeError):
            MediaType.parse("text/html; ")
        with self.assertRaises(InvalidMediaTypeError):
            MediaType.parse("text/html; charset")


class MediaTypeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = MediaTypeRegistry()

    def test_is_valid_known(self):
        self.assertTrue(self.registry.is_valid("text/html"))
        self.assertTrue(self.registry.is_valid("TEXT/HTML"))
        self.assertTrue(self.registry.is_valid("text/html; charset=utf-8"))

    def test_is_valid_unknown(self):
        self.assertFalse(self.registry.is_valid("text/nope"))

    def test_is_valid_invalid_syntax(self):
        self.assertFalse(self.registry.is_valid("not a media type"))

    def test_contains(self):
        self.assertIn("application/json", self.registry)
        self.assertIn(MediaType.parse("application/json"), self.registry)
        self.assertNotIn("application/nope", self.registry)
        self.assertNotIn(42, self.registry)

    def test_lookup_returns_media_type(self):
        mt = self.registry.lookup("application/json")
        self.assertIsInstance(mt, MediaType)
        self.assertEqual(mt.full_type, "application/json")

    def test_lookup_unknown_raises(self):
        with self.assertRaises(UnknownMediaTypeError):
            self.registry.lookup("application/nope")

    def test_lookup_invalid_raises(self):
        with self.assertRaises(InvalidMediaTypeError):
            self.registry.lookup("nope")

    def test_extensions_for(self):
        self.assertEqual(self.registry.extensions_for("text/html"), ("html", "htm"))
        self.assertEqual(self.registry.extensions_for("application/json"), ("json",))

    def test_extensions_for_no_mapping(self):
        self.assertEqual(self.registry.extensions_for("message/http"), ())

    def test_media_types_for_extension(self):
        self.assertEqual(self.registry.media_types_for_extension("png"), ("image/png",))
        self.assertEqual(self.registry.media_types_for_extension(".PNG"), ("image/png",))

    def test_media_types_for_extension_unknown(self):
        with self.assertRaises(UnknownMediaTypeError):
            self.registry.media_types_for_extension("nope")

    def test_media_types_for_extension_ambiguous(self):
        with self.assertRaises(AmbiguousExtensionError):
            self.registry.media_types_for_extension("ts")

    def test_all_media_types_for_extension(self):
        self.assertEqual(
            self.registry.all_media_types_for_extension("ts"),
            ("text/typescript", "video/mp2t"),
        )
        self.assertEqual(self.registry.all_media_types_for_extension("nope"), ())

    def test_all_media_types_for_extension_empty(self):
        self.assertEqual(self.registry.all_media_types_for_extension("."), ())

    def test_all_media_types_for_extension_non_string(self):
        with self.assertRaises(InvalidMediaTypeError):
            self.registry.all_media_types_for_extension(123)  # type: ignore[arg-type]

    def test_types_and_extensions_sorted(self):
        types = self.registry.types()
        self.assertEqual(types, tuple(sorted(types)))
        self.assertIn("text/html", types)
        extensions = self.registry.extensions()
        self.assertEqual(extensions, tuple(sorted(extensions)))
        self.assertIn("html", extensions)

    def test_registry_is_isolated_from_module_data(self):
        # Mutating the returned tuple should not be possible (tuples are
        # immutable), and a second registry should still see the original
        # data even if we could mutate the first.
        first = MediaTypeRegistry()
        second = MediaTypeRegistry()
        self.assertEqual(first.extensions_for("text/html"), second.extensions_for("text/html"))


if __name__ == "__main__":
    unittest.main()
