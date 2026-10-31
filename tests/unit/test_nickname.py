import pytest

from rooms.nickname import validate_nickname


@pytest.mark.parametrize("raw,expected", [
    ("Alice", "Alice"),
    ("  Bob  ", "Bob"),
    ("a" * 16, "a" * 16),
    ("meen-shei", "meen-shei"),
    ("player_1", "player_1"),
    ("A b", "A b"),
])
def test_valid(raw, expected):
    nick, err = validate_nickname(raw)
    assert err is None
    assert nick == expected


@pytest.mark.parametrize("raw,code", [
    ("", "NICKNAME_TOO_SHORT"),
    ("a", "NICKNAME_TOO_SHORT"),
    ("  ", "NICKNAME_TOO_SHORT"),
    ("a" * 17, "NICKNAME_TOO_LONG"),
    ("bad!", "NICKNAME_INVALID_CHARS"),
    ("bad@", "NICKNAME_INVALID_CHARS"),
    ("emoji😀", "NICKNAME_INVALID_CHARS"),
    (123, "INVALID_NICKNAME"),
    (None, "INVALID_NICKNAME"),
    (["Alice"], "INVALID_NICKNAME"),
])
def test_invalid(raw, code):
    nick, err = validate_nickname(raw)
    assert nick is None
    assert err == code


def test_strip_before_length_check():
    nick, err = validate_nickname(" a ")
    assert nick is None
    assert err == "NICKNAME_TOO_SHORT"

    nick, err = validate_nickname(" ab ")
    assert nick == "ab"
    assert err is None