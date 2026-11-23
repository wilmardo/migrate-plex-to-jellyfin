#!/usr/bin/env python3

from typing import List, Set, NamedTuple

import requests
import urllib3
import click
import sys
from datetime import datetime
from loguru import logger

from plexapi.server import PlexServer
from plexapi import library
from plexapi.media import Media
from plexapi.utils import setDatetimeTimezone
from jellyfin_client import JellyFinServer


LOG_FORMAT = ("<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
              "<level>{level: <8}</level> | "
              "<level>{message}</level> | "
              "{extra}")


class PathTranslation(NamedTuple):
    src: str
    dst: str


TranslationLib = List[PathTranslation]


def build_translation_library(args: List[str]) -> TranslationLib:
    tranlations: TranslationLib = []

    for arg in args:
        src, dst = arg.split("|", 1)

        tranlations.append(PathTranslation(src=src, dst=dst))

    return tranlations


def translate_path(path: str, translations: TranslationLib) -> str:
    tr_path = path

    for t in translations:
        if tr_path.startswith(t.src):
            tr_path = t.dst + tr_path[len(t.src) :]

            # If dst is Linux-ish, normalise to forward slashes
            if "/" in t.dst and "\\" in tr_path:
                tr_path = tr_path.replace("\\", "/")
            # If dst is Windows-ish, normalise to backslashes
            elif "\\" in t.dst and "/" in tr_path:
                tr_path = tr_path.replace("/", "\\")

    return tr_path


@click.command()
@click.option('--plex-url', required=True, help='Plex server url')
@click.option('--plex-token', required=True, help='Plex token')
@click.option('--plex-managed-user', help='Name of a managed user')
@click.option('--jellyfin-url', required=True, help='Jellyfin server url')
@click.option('--jellyfin-token', required=True, help='Jellyfin token')
@click.option('--jellyfin-user', required=True, help='Jellyfin user')
@click.option("--translate", help="Path translation", type=str, multiple=True, default=[])
@click.option('--secure/--insecure', help='Verify SSL')
@click.option('--debug/--no-debug', help='Print more output')
@click.option('--no-skip/--skip', help='Skip when no match it found instead of exiting')
@click.option('--dry-run', is_flag=True, help='Do not commit changes to Jellyfin')
def migrate(plex_url: str, plex_token: str, plex_managed_user: str, jellyfin_url: str,
            jellyfin_token: str, jellyfin_user: str,
            translate: List[str],
            secure: bool, debug: bool, no_skip: bool, dry_run: bool):

    logger.remove()
    if debug:
        logger.add(sys.stderr, format=LOG_FORMAT, level="DEBUG")
    else:
        logger.add(sys.stderr, format=LOG_FORMAT, level="INFO")

    # Remove insecure request warnings
    if not secure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Ensure Plex API returns time zone data.
    # Note that, by default, the Plex Python API returns "naive" datetime
    # objects, without time zone data, but converted from UTC to "local" time.
    # We need time zone data to make sure we can properly convert it back to
    # UTC for Jellyfin! (Added in Plex API version `4.18.1`.)
    setDatetimeTimezone(True)

    # Setup sessions
    session = requests.Session()
    session.verify = secure
    plex = PlexServer(plex_url, plex_token, session=session)

    jellyfin = JellyFinServer(
        url=jellyfin_url, api_key=jellyfin_token, session=session)

    # Override the Plex session for a managed user
    if plex_managed_user:
        managed_account = plex.myPlexAccount().user(plex_managed_user)
        managed_token = managed_account.get_token(plex.machineIdentifier)
        plex = PlexServer(plex_url, managed_token, session=session)

    # Watched list from Plex
    # A dictionary of "file path" -> "last watched datetime". Note that in
    # cases where there are multiple parts to a media entry, all paths will
    # have the same datetime value.
    plex_watched_dict: dict[str, datetime] = {}

    # All the items in jellyfish:
    logger.info("Loading Jellyfin Items...")
    jf_uid = jellyfin.get_user_id(name=jellyfin_user)
    jf_library = jellyfin.get_all(user_id=jf_uid)
    jf_entries: dict[str, List[dict]] = {} # map of path -> jf library entry
    for jf_entry in jf_library:
        for source in jf_entry.get("MediaSources", []):
            if "Path" not in source:
                continue
            if source["Path"] not in jf_entries:
                jf_entries[source["Path"]] = [jf_entry]
            else:
                jf_entries[source["Path"]].append(jf_entry)
            logger.bind(path=source["Path"], id=jf_entry["Id"]).debug("jf entry")

    # Get all Plex watched movies
    logger.info("Loading Plex Watched Items...")
    for section in plex.library.sections():
        if isinstance(section, library.MovieSection):
            plex_movies = section
            for m in plex_movies.search(unwatched=False):
                # Note call to `astimezone()` here -- if time zone data is
                # still missing, this will properly set it to "local",
                # accounting for Daylight Savings, etc.
                _warn_if_no_time_zone(m)
                parts_dict = _watch_parts(m.media, m.lastViewedAt.astimezone())
                plex_watched_dict.update(parts_dict)
                logger.bind(section=section.title, movie=m, parts=parts_dict).debug("watched movie")
        elif isinstance(section, library.ShowSection):
            plex_tvshows = section
            for show in plex_tvshows.searchShows(**{"episode.unwatched": False}):
                for e in show.watched():
                    _warn_if_no_time_zone(e)
                    parts_dict = _watch_parts(e.media, e.lastViewedAt.astimezone())
                    plex_watched_dict.update(parts_dict)
                    logger.bind(section=section.title, ep=e, parts=parts_dict).debug("watched episode")

    tr_library = build_translation_library(translate)

    marked = 0
    missing = 0
    skipped = 0
    for watched, lastViewedAt in plex_watched_dict.items():

        tr_watched = translate_path(watched, tr_library)

        if tr_watched not in jf_entries:
            logger.bind(path=tr_watched).warning("no match found on jellyfin")
            missing += 1
            continue
        for jf_entry in jf_entries[tr_watched]:
            if not jf_entry["UserData"]["Played"]:
                marked += 1
                if dry_run:
                    message = "Would be marked as watched (dry run)"
                else:
                    jellyfin.mark_watched(user_id=jf_uid, item_id=jf_entry["Id"])
                    message = "Marked as watched"
                logger.bind(path=tr_watched, watch_time=lastViewedAt, jf_id=jf_entry["Id"], title=jf_entry["Name"]).info(message)
            else:
                skipped += 1
                logger.bind(path=tr_watched, jf_id=jf_entry["Id"], title=jf_entry["Name"]).debug("Skipped marking already-watched media")

    message = "Succesfully migrated watched states to Jellyfin"
    if dry_run:
        message = "Would migrate watched states to Jellyfin"
    logger.bind(updated=marked, missing=missing, skipped=skipped).success(message)


def _warn_if_no_time_zone(m):
    """Warn if Plex "last watched" datetimes are missing time zones. We handle
    this case so it shouldn't matter too much, but it's still an indicator of
    something weird going on."""
    lastViewedAt = m.lastViewedAt
    if not lastViewedAt.tzinfo:
        logger.bind(media=m, last_watched=lastViewedAt).warning("no time zone data included in Plex result")


def _watch_parts(media: List[Media], last_viewed_at: datetime) -> dict[str, datetime]:
    """Extract all filenames from a given media item and attach "last watched" datetime."""
    watched_dict: dict[str, datetime] = {}
    for medium in media:
        # Note that all the "parts" have the same `last_viewed_at` value:
        watched_dict.update(map(lambda p: (p.file, last_viewed_at), medium.parts))
    return watched_dict

if __name__ == '__main__':
    migrate()
