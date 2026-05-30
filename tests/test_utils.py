from pathlib import Path

from rich.tree import Tree

from htr_prep.utils import (
    build_tree,
    get_custom_field,
    normalize_region,
    parse_reading_order,
)


class TestNormalizeRegion:
    def test_strips_tr_prefix_and_returns_digits(self):
        assert normalize_region("tr_1") == "1"
        assert normalize_region("tr_42") == "42"

    def test_passes_through_non_prefixed_id(self):
        assert normalize_region("r") == "r"
        assert normalize_region("region_abc") == "region_abc"

    def test_handles_empty_string(self):
        assert normalize_region("") == ""

    def test_handles_none(self):
        # signature is `str`, but runtime guard `region_id or ""` makes None safe
        assert normalize_region(None) == ""  # type: ignore[arg-type]

    def test_does_not_match_partial(self):
        # ^tr_(\d+)$ is anchored — trailing chars or extra prefix must not match
        assert normalize_region("tr_1a") == "tr_1a"
        assert normalize_region("xtr_1") == "xtr_1"


class TestParseReadingOrder:
    def test_extracts_index(self):
        assert parse_reading_order("readingOrder {index:3;}") == 3

    def test_tolerates_missing_whitespace(self):
        assert parse_reading_order("readingOrder{index:7;}") == 7

    def test_picks_index_from_compound_custom_string(self):
        custom = "structure {type:paragraph;} readingOrder {index:11;}"
        assert parse_reading_order(custom) == 11

    def test_returns_none_when_absent(self):
        assert parse_reading_order("structure {type:foo;}") is None

    def test_returns_none_for_empty_inputs(self):
        assert parse_reading_order("") is None
        assert parse_reading_order(None) is None


class TestGetCustomField:
    def test_extracts_named_field(self):
        custom = "readingOrder {index:5;} structure {type:paragraph;}"
        assert get_custom_field(custom, "structure", "type") == "paragraph"
        assert get_custom_field(custom, "readingOrder", "index") == "5"

    def test_returns_none_for_missing_group(self):
        custom = "structure {type:foo;}"
        assert get_custom_field(custom, "readingOrder", "index") is None

    def test_returns_none_for_missing_key_within_group(self):
        custom = "structure {type:foo;}"
        assert get_custom_field(custom, "structure", "offset") is None


class TestBuildTree:
    def test_returns_rich_tree(self):
        tree = build_tree([Path("data"), Path("data/images")])
        assert isinstance(tree, Tree)

    def test_empty_input_returns_empty_tree(self):
        tree = build_tree([])
        assert isinstance(tree, Tree)
        assert tree.children == []

    def test_dedupes_shared_parents(self):
        dirs = [
            Path("data/images"),
            Path("data/xml_texts"),
            Path("dataset/images/train"),
            Path("dataset/images/val"),
        ]
        tree = build_tree(dirs)
        # exactly two top-level branches: "data" and "dataset"
        assert len(tree.children) == 2
