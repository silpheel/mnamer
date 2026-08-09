import datetime as dt
import sys
from pathlib import Path

import pytest

from mnamer.metadata import MetadataEpisode, MetadataMovie
from mnamer.setting_store import SettingStore
from mnamer.target import Target
from mnamer.types import MediaType

pytestmark = pytest.mark.local


def test_parse__media__movie():
    target = Target(Path("ninja turtles (1990).mkv"), SettingStore())
    assert target.metadata.to_media_type() is MediaType.MOVIE


def test_parse__media__episode():
    target = Target(Path("ninja turtles s01e01.mkv"), SettingStore())
    assert target.metadata.to_media_type() is MediaType.EPISODE


def test_parse__quality():
    file_path = Path("ninja.turtles.s01e04.1080p.ac3.rargb.sample.mkv")
    target = Target(file_path, SettingStore())
    assert target.metadata.quality == "1080p dolby digital"


def test_parse__group():
    file_path = Path("ninja.turtles.s01e04.1080p.ac3.rargb.sample.mkv")
    target = Target(file_path, SettingStore())
    assert target.metadata.group == "RARGB"


def test_parse__container():
    file_path = Path("ninja.turtles.s01e04.1080p.ac3.rargb.sample.mp4")
    target = Target(file_path, SettingStore())
    assert target.metadata.container == ".mp4"


def test_parse__date():
    file_path = Path("the.colbert.show.2010.10.01.avi")
    target = Target(file_path, SettingStore())
    assert isinstance(target.metadata, MetadataEpisode)
    assert target.metadata.date == dt.date(2010, 10, 1)


def test_parse__episode():
    file_path = Path("ninja.turtles.s01e04.1080p.ac3.rargb.sample.mp4")
    target = Target(file_path, SettingStore())
    assert isinstance(target.metadata, MetadataEpisode)
    assert target.metadata.episode == 4


def test_parse__season():
    file_path = Path("ninja.turtles.s01e04.1080p.ac3.rargb.sample.mp4")
    target = Target(file_path, SettingStore())
    assert isinstance(target.metadata, MetadataEpisode)
    assert target.metadata.season == 1


def test_parse__season__assumes_first_season_for_two_digit_episode():
    file_path = Path("anime.turtles.02.1080p.ac3.rargb.sample.mp4")
    target = Target(file_path, SettingStore())
    assert isinstance(target.metadata, MetadataEpisode)
    assert target.metadata.season == 1
    assert target.metadata.episode == 2


def test_parse__season__uses_ordinal_season_in_series_title():
    target = Target(
        Path("Kabushikigaisha Magilumiere 2nd Season - 05.mkv"),
        SettingStore(media=MediaType.EPISODE),
    )
    assert isinstance(target.metadata, MetadataEpisode)
    assert target.metadata.season == 2
    assert target.metadata.episode == 5


def test_parse__season__uses_numbered_season_in_series_title():
    target = Target(
        Path("Some Series Season 3 - 05.mkv"),
        SettingStore(media=MediaType.EPISODE),
    )
    assert isinstance(target.metadata, MetadataEpisode)
    assert target.metadata.season == 3
    assert target.metadata.episode == 5


def test_parse__episode__retries_filename_when_season_directory_hides_episode():
    target = Target(
        Path(
            "Season 01/"
            "[Erai-raws] Heroine Seijo Iie All Works Maid desu (Hokori) - 02 "
            "[720p CR WEB-DL AVC AAC][MultiSub][D294E1F9].mkv"
        ),
        SettingStore(),
    )
    assert isinstance(target.metadata, MetadataEpisode)
    assert target.metadata.season == 1
    assert target.metadata.episode == 2


@pytest.mark.parametrize(
    ("series", "expected_series"),
    [
        ("one-punch man", "One-Punch Man"),
        ("Plus-sized misadventures in love", "Plus-Sized Misadventures in Love"),
        ("K-On!", "K-On!"),
    ],
)
def test_parse__episode__preserves_dashes_in_parent_and_filename(
    series, expected_series
):
    target = Target(
        Path(f"{series}/Season 01/{series} - 01.mkv"),
        SettingStore(media=MediaType.EPISODE),
    )

    assert target.metadata.series == expected_series
    assert target.metadata.season == 1
    assert target.metadata.episode == 1


def test_parse__episode__uses_dashed_series_parent_when_filename_has_only_episode():
    target = Target(
        Path("one-punch man/Season 01/01.mkv"),
        SettingStore(media=MediaType.EPISODE),
    )

    assert target.metadata.series == "One-Punch Man"
    assert target.metadata.season == 1
    assert target.metadata.episode == 1


def test_parse__episode__uses_parent_series_for_episode_prefixed_filename():
    target = Target(
        Path("Pluto (2024)/Season 01/S01E01 - Episode 1.mkv"),
        SettingStore(media=MediaType.EPISODE),
    )

    assert target.metadata.series == "Pluto"
    assert target.metadata.season == 1
    assert target.metadata.episode == 1
    assert target.metadata.title == "Episode 1"


def test_parse__movie__retains_alternative_title_from_sanitized_filename():
    target = Target(
        Path("Title - Subtitle.mkv"),
        SettingStore(media=MediaType.MOVIE),
    )

    assert target.metadata.name == "Title"


def test_parse__episode__does_not_append_episode_title_to_series():
    target = Target(
        Path("Series - Episode S01E01.mkv"),
        SettingStore(media=MediaType.EPISODE),
    )

    assert target.metadata.series == "Series"
    assert target.metadata.title == "Episode"


def test_parse__episode__explicit_three_digit_episode_with_release_suffix():
    target = Target(
        Path("Dragonball Z Kai S01E157CC.mkv"),
        SettingStore(media=MediaType.EPISODE),
    )
    assert target.metadata.season == 1
    assert target.metadata.episode == 157


def test_parse__episode__assumes_first_season_for_clean_three_digit_episode():
    target = Target(
        Path("Dragonball Z Kai - 157.mkv"),
        SettingStore(media=MediaType.EPISODE),
    )
    assert target.metadata.season == 1
    assert target.metadata.episode == 157


def test_parse__season__does_not_assume_for_one_digit_episode():
    target = Target(Path("Some Series - 2.mkv"), SettingStore(media=MediaType.EPISODE))
    assert isinstance(target.metadata, MetadataEpisode)
    assert target.metadata.season is None


def test_parse__season__normalizes_single_item_episode_lists(mocker):
    mocker.patch(
        "mnamer.target.guessit",
        return_value={"title": "Some Series", "episode": [2]},
    )
    target = Target(Path("Some Series - 02.mkv"), SettingStore(media=MediaType.EPISODE))

    assert target.metadata.season == 1
    assert target.metadata.episode == 2


def test_parse__series():
    file_path = Path("ninja.turtles.s01e04.1080p.ac3.rargb.sample.mp4")
    target = Target(file_path, SettingStore())
    assert isinstance(target.metadata, MetadataEpisode)
    assert target.metadata.series == "Ninja Turtles"


def test_parse__year():
    file_path = Path("the.goonies.1985")
    target = Target(file_path, SettingStore())
    assert isinstance(target.metadata, MetadataMovie)
    assert target.metadata.year == 1985


def testparse__name():
    file_path = Path("the.goonies.1985")
    target = Target(file_path, SettingStore())
    assert isinstance(target.metadata, MetadataMovie)
    assert target.metadata.name == "The Goonies"


@pytest.mark.parametrize("media", MediaType)
def test_media__override(media: MediaType):
    target = Target(Path(), SettingStore(media=media))
    assert target.metadata.to_media_type() == media


def test_directory__movie():
    movie_path = Path("/some/movie/path").absolute()
    target = Target(
        Path(), SettingStore(media=MediaType.MOVIE, movie_directory=movie_path)
    )
    assert target.directory == movie_path


def test_directory__episode():
    episode_path = Path("/some/episode/path").absolute()
    target = Target(
        Path(),
        SettingStore(media=MediaType.EPISODE, episode_directory=episode_path),
    )
    assert target.directory == episode_path


def test_ambiguous_subtitle_language():
    target = Target(
        Path("Subs/Nancy.Drew.S01E01.WEBRip.x264-ION10.srt"), SettingStore()
    )
    assert target.metadata.language is None


def test_destination__simple():
    pass  # TODO


@pytest.mark.parametrize(
    ("filename", "same_as_destination"),
    [
        ("S01E01 My Title Here.mkv", False),
        ("Series - S01E01 - My Title Changed.mkv", False),
        ("Series - S01E01 - My Title Here.mkv", True),
    ],
)
def test_destination__episode_round_trip_is_stable(filename, same_as_destination):
    target = Target(Path("Series/Season 01") / filename, SettingStore())
    target.metadata.update(
        MetadataEpisode(series="Series", season=1, episode=1, title="My Title Here")
    )

    assert (target.destination == target.source.resolve()) is same_as_destination


def test_destination__relative_directory_lowered():
    """Every part of a relative configured directory receives --lower."""
    settings = SettingStore(
        batch=True,
        media=MediaType.MOVIE,
        lower=True,
        movie_directory=Path("Movies/{name[0]}"),
    )
    target = Target(Path("ninja turtles (1990).mkv"), settings)
    assert target.destination == Path("movies/n/ninja turtles (1990).mkv").resolve()


@pytest.mark.skipif(
    sys.platform == "win32", reason="Unix path test, not valid on Windows"
)
def test_destination__absolute_directory_preserves_literal_parts():
    """Literal parts of an absolute configured directory survive --lower."""
    settings = SettingStore(
        batch=True,
        media=MediaType.MOVIE,
        lower=True,
        movie_directory=Path("/Media Library/Movies"),
    )
    target = Target(Path("ninja turtles (1990).mkv"), settings)
    assert target.destination == Path("/Media Library/Movies/ninja turtles (1990).mkv")


@pytest.mark.skipif(
    sys.platform == "win32", reason="Unix path test, not valid on Windows"
)
def test_destination__absolute_directory_transforms_template_parts():
    """Template parts within an absolute configured directory are transformed."""
    settings = SettingStore(
        batch=True,
        media=MediaType.MOVIE,
        lower=True,
        movie_directory=Path("/Media Library/{name[0]}"),
    )
    target = Target(Path("ninja turtles (1990).mkv"), settings)
    assert target.destination == Path("/Media Library/n/ninja turtles (1990).mkv")


def test_destination__format_template_directory_components_transformed():
    """Directory components emitted by the format template are post-processed."""
    settings = SettingStore(
        batch=True,
        media=MediaType.MOVIE,
        lower=True,
        movie_format="{name}/{name} ({year}).{extension}",
    )
    target = Target(Path("ninja turtles (1990).mkv"), settings)
    assert (
        target.destination == Path("ninja turtles/ninja turtles (1990).mkv").resolve()
    )


def test_destination__relative_directory_scene():
    """--scene applies to literal and templated parts of a relative directory."""
    settings = SettingStore(
        batch=True,
        media=MediaType.MOVIE,
        scene=True,
        movie_directory=Path("Movie Library/{name}"),
    )
    target = Target(Path("ninja turtles (1990).mkv"), settings)
    assert (
        target.destination
        == Path("movie.library/ninja.turtles/ninja.turtles.1990.mkv").resolve()
    )


@pytest.mark.skipif(
    sys.platform == "win32", reason="Unix path test, not valid on Windows"
)
def test_destination__absolute_directory_scene_preserves_literal_parts():
    """Literal parts of an absolute configured directory survive --scene."""
    settings = SettingStore(
        batch=True,
        media=MediaType.MOVIE,
        scene=True,
        movie_directory=Path("/Media Library/Movies"),
    )
    target = Target(Path("ninja turtles (1990).mkv"), settings)
    assert target.destination == Path("/Media Library/Movies/ninja.turtles.1990.mkv")


@pytest.mark.skipif(
    sys.platform == "win32", reason="Unix path test, not valid on Windows"
)
def test_destination__absolute_directory_scene_transforms_template_parts():
    """Template parts within an absolute configured directory survive --scene."""
    settings = SettingStore(
        batch=True,
        media=MediaType.MOVIE,
        scene=True,
        movie_directory=Path("/Media Library/{name}"),
    )
    target = Target(Path("ninja turtles (1990).mkv"), settings)
    assert target.destination == Path(
        "/Media Library/ninja.turtles/ninja.turtles.1990.mkv"
    )


def test_destination__parent_directory_navigation_preserved():
    """A `..` segment in a relative directory survives sanitization."""
    settings = SettingStore(
        batch=True,
        media=MediaType.MOVIE,
        lower=True,
        movie_directory=Path("../Movies"),
    )
    target = Target(Path("ninja turtles (1990).mkv"), settings)
    assert target.destination == Path("../movies/ninja turtles (1990).mkv").resolve()


def test_destination__same_directory_matches_source(tmp_path, monkeypatch):
    """`--movie_directory=.` resolves to the source path so the no-op is skippable."""
    tmp = tmp_path.resolve()
    monkeypatch.chdir(tmp)
    source = tmp / "Ninja Turtles (1990).mkv"
    source.touch()
    settings = SettingStore(
        batch=True,
        media=MediaType.MOVIE,
        movie_directory=Path("."),
    )
    target = Target(source, settings)
    assert target.destination == target.source


def test_query():
    pass  # TODO


def test_query__filters_results_to_parsed_episode(mocker):
    target = Target(Path("Some Series - 02.mkv"), SettingStore(media=MediaType.EPISODE))
    target._provider = mocker.Mock()
    target._provider.search.return_value = [
        MetadataEpisode(series="Some Series", season=1, episode=1),
        MetadataEpisode(series="Some Series", season=1, episode=2),
        MetadataEpisode(series="Some Series", season=2, episode=2),
    ]

    results = target.query()

    assert [(result.season, result.episode) for result in results] == [(1, 2)]


def test_relocate():
    pass  # TODO
