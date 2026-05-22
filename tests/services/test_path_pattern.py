import pytest

from rapis.services.path_pattern import compile_path_pattern, path_captures


@pytest.mark.parametrize("path", ("/{user_id}", "/some/{data}"))
def test_path_pattern_compiles_with_fields(path: str) -> None:
    _, fields = compile_path_pattern(path)
    assert len(fields)


@pytest.mark.parametrize(
    "path",
    ("/{user_id", "/some/data}", "/sdf/{sdfsd/sdffs}"),
)
def test_path_pattern_incorrect_syntax_no_named_params(path: str) -> None:
    _, fields = compile_path_pattern(path)
    assert not len(fields)


def test_path_captures_no_regex_returns_empty() -> None:
    assert path_captures(None, "/") == {}


def test_path_captures_extracts_named_groups() -> None:
    pat, _ = compile_path_pattern("/users/{pk}/posts/{slug}")
    assert path_captures(pat, "/users/42/posts/hello") == {
        "pk": "42",
        "slug": "hello",
    }
