"""Tests for verify_signature, using the example values GitHub publishes in its webhook docs."""

from app.security import verify_signature

SECRET = "It's a Secret to Everybody"
BODY = b"Hello, World!"
HEADER = "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"


def test_valid_signature_is_accepted() -> None:
    assert verify_signature(SECRET, BODY, HEADER) is True


def test_wrong_secret_is_rejected() -> None:
    assert verify_signature("wrong-secret", BODY, HEADER) is False


def test_changed_body_is_rejected() -> None:
    assert verify_signature(SECRET, b"Hello, World?", HEADER) is False


def test_missing_header_is_rejected() -> None:
    assert verify_signature(SECRET, BODY, None) is False
    assert verify_signature(SECRET, BODY, "") is False


def test_header_without_prefix_is_rejected() -> None:
    assert verify_signature(SECRET, BODY, HEADER.removeprefix("sha256=")) is False
