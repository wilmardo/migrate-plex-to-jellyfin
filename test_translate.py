"""Test the translate path feature."""

from migrate import PathTranslation, build_translation_library, translate_path

EXAMPLE_FILENAME = "Meet the Press (1947)/Season 2020/S2020E01 - January 5, 2020 [SDTV x264 AAC].mp4"


def test_build_library() -> None:
    assert build_translation_library(
        [
            "/media|/mnt/media",
        ]
    ) == [
        PathTranslation("/media", "/mnt/media"),
    ]


def test_translate_path_empty() -> None:
    """Test translate_path with an empty translation set."""
    assert translate_path("foo", []) == "foo"


def test_translate_path_simple() -> None:
    """Test translate_path with a simple single translation."""
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
    """Test translate_path uses the first matching translation."""
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
    """Test translate_path applying chained translations across multiple calls."""
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


def test_translate_path_windows_to_linux_normalizes_separators() -> None:
    """Windows-style Plex path should translate to Linux-style and normalize slashes."""
    plex_path = rf"D:\Media\television\{EXAMPLE_FILENAME}"
    assert (
        translate_path(
            plex_path,
            [
                PathTranslation(r"D:\Media", "/mnt/media"),
            ],
        )
        == f"/mnt/media/television/{EXAMPLE_FILENAME}"
    )


def test_translate_path_linux_to_windows_normalizes_separators() -> None:
    """Linux-style path should translate to Windows-style and normalize slashes."""
    linux_path = f"/mnt/media/television/{EXAMPLE_FILENAME}"
    assert (
        translate_path(
            linux_path,
            [
                PathTranslation("/mnt/media", r"D:\Media"),
            ],
        )
        == rf"D:\Media\television\{EXAMPLE_FILENAME}"
    )


def test_translate_path_build_library_windows_mapping() -> None:
    """Ensure build_translation_library handles Windows src/dst with the '|' delimiter."""
    assert build_translation_library(
        [
            r"D:\Media|/mnt/media",
        ]
    ) == [
        PathTranslation(r"D:\Media", "/mnt/media"),
    ]
