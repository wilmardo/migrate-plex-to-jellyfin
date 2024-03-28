"""Test the translate path feature."""

from migrate import PathTranslation, build_translation_library, translate_path

EXAMPLE_FILENAME = "Meet the Press (1947)/Season 2020/S2020E01 - January 5, 2020 [SDTV x264 AAC].mp4"

def test_build_library() -> None:
    assert build_translation_library(
        [
            "/media:/mnt/media",
        ]
    ) == [
        PathTranslation("/media", "/mnt/media"),
    ]


def test_translate_path_empty() -> None:
    """Test translate_path with an empty translation set."""

    assert translate_path("foo", []) == "foo"


def test_translate_path_simple() -> None:
    """Test translate_path with an empty translation set."""

    assert (
        translate_path(
            f"/media/television/{EXAMPLE_FILENAME}",
            [
                PathTranslation("/media", "/mnt/media"),
            ],
        )
        == f"/mnt/media/television/{EXAMPLE_FILENAME}"
    )


def test_translate_path_one_of_many() -> None:
    """Test translate_path with an empty translation set."""

    assert (
        translate_path(
            f"/media/television/{EXAMPLE_FILENAME}",
            [
                PathTranslation("/media", "/mnt/media"),
                PathTranslation("/television", "/mnt/media/television"),
            ],
        )
        == f"/mnt/media/television/{EXAMPLE_FILENAME}"
    )


def test_translate_path_multiple() -> None:
    """Test translate_path with an empty translation set."""

    assert (
        translate_path(
            f"/media/television/{EXAMPLE_FILENAME}",
            [
                PathTranslation("/media", "/mnt/media"),
                PathTranslation("/mnt/media/television", "/tv"),
            ],
        )
        == f"/tv/{EXAMPLE_FILENAME}"
    )
