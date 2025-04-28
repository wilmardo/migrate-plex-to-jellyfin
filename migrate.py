from typing import List, Set, Dict, Optional

import requests
import urllib3
import click
import sys
from loguru import logger

from plexapi.server import PlexServer
from plexapi import library
from plexapi.media import Media
from jellyfin_client import JellyFinServer


LOG_FORMAT = ("<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
              "<level>{level: <8}</level> | "
              "<level>{message}</level> | "
              "{extra}")

@click.command()
@click.option('--plex-url', required=True, help='Plex server url')
@click.option('--plex-token', required=True, help='Plex token')
@click.option('--plex-managed-user', help='Name of a managed user')
@click.option('--jellyfin-url', required=True, help='Jellyfin server url')
@click.option('--jellyfin-token', required=True, help='Jellyfin token')
@click.option('--jellyfin-user', required=True, help='Jellyfin user')
@click.option('--folder-mapping', multiple=True, help='Map Plex folder to Jellyfin folder (format: "plex_path:jellyfin_path")')
@click.option('--secure/--insecure', help='Verify SSL')
@click.option('--debug/--no-debug', help='Print more output')
@click.option('--no-skip/--skip', help='Skip when no match it found instead of exiting')
@click.option('--dry-run', is_flag=True, help='Do not commit changes to Jellyfin')
def migrate(plex_url: str, plex_token: str, plex_managed_user: str, jellyfin_url: str,
            jellyfin_token: str, jellyfin_user: str, folder_mapping: List[str],
            secure: bool, debug: bool, no_skip: bool, dry_run: bool):
    logger.remove()
    if debug:
        logger.add(sys.stderr, format=LOG_FORMAT, level="DEBUG")
    else:
        logger.add(sys.stderr, format=LOG_FORMAT, level="INFO")

    # Process folder mappings
    path_mappings: Dict[str, str] = {}
    for mapping in folder_mapping:
        try:
            plex_path, jellyfin_path = mapping.split(":", 1)
            path_mappings[plex_path] = jellyfin_path
            logger.bind(plex_path=plex_path, jellyfin_path=jellyfin_path).debug("Added folder mapping")
        except ValueError:
            logger.bind(mapping=mapping).warning("Invalid folder mapping format, expected 'plex_path:jellyfin_path'")

    # Remove insecure request warnings
    if not secure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    plex_watched = set()

    # All the items in jellyfish:
    jf_uid = jellyfin.get_user_id(name=jellyfin_user)
    jf_library = jellyfin.get_all(user_id=jf_uid)
    jf_entries: dict[str, List[dict]] = {} # map of path -> jf library entry
    for jf_entry in jf_library:
        for source in jf_entry.get("MediaSources", []):
            if source["Path"] not in jf_entries:
                jf_entries[source["Path"]] = [jf_entry]
            else:
                jf_entries[source["Path"]].append(jf_entry)
            logger.bind(path=source["Path"], id=jf_entry["Id"]).debug("jf entry")

    # Get all Plex watched movies
    for section in plex.library.sections():
        if isinstance(section, library.MovieSection):
            plex_movies = section
            for m in plex_movies.search(unwatched=False):
                parts=_watch_parts(m.media)
                plex_watched.update(parts)
                logger.bind(section=section.title, movie=m, parts=parts).debug("watched movie")
        elif isinstance(section, library.ShowSection):
            plex_tvshows = section
            for show in plex_tvshows.searchShows(**{"episode.unwatched": False}):
                for e in show.watched():
                    parts=_watch_parts(e.media)
                    plex_watched.update(parts)
                    logger.bind(section=section.title, ep=e, parts=parts).debug("watched episode")


    marked = 0
    missing = 0
    skipped = 0
    for watched in plex_watched:
        # Apply path mapping if applicable
        mapped_path = _map_path(watched, path_mappings)
        logger.bind(original=watched, mapped=mapped_path).debug("Path mapping")
        
        if mapped_path in jf_entries:
            # Found a match with the mapped path
            for jf_entry in jf_entries[mapped_path]:
                if not jf_entry["UserData"]["Played"]:
                    marked += 1
                    if dry_run:
                        message = "Would be marked as watched (dry run)"
                    else:
                        jellyfin.mark_watched(user_id=jf_uid, item_id=jf_entry["Id"])
                        message = "Marked as watched"
                    logger.bind(path=mapped_path, jf_id=jf_entry["Id"], title=jf_entry["Name"]).info(message)
                else:
                    skipped += 1
                    logger.bind(path=mapped_path, jf_id=jf_entry["Id"], title=jf_entry["Name"]).debug("Skipped marking already-watched media")
        else:
            # Try with original path if no match found with mapped path
            if watched in jf_entries:
                for jf_entry in jf_entries[watched]:
                    if not jf_entry["UserData"]["Played"]:
                        marked += 1
                        if dry_run:
                            message = "Would be marked as watched (dry run)"
                        else:
                            jellyfin.mark_watched(user_id=jf_uid, item_id=jf_entry["Id"])
                            message = "Marked as watched"
                        logger.bind(path=watched, jf_id=jf_entry["Id"], title=jf_entry["Name"]).info(message)
                    else:
                        skipped += 1
                        logger.bind(path=watched, jf_id=jf_entry["Id"], title=jf_entry["Name"]).debug("Skipped marking already-watched media")
            else:
                logger.bind(path=watched, mapped_path=mapped_path).warning("no match found on jellyfin")
                missing += 1

    message = "Succesfully migrated watched states to Jellyfin"
    if dry_run:
        message = "Would migrate watched states to Jellyfin"
    logger.bind(updated=marked, missing=missing, skipped=skipped).success(message)


def _watch_parts(media: List[Media]) -> Set[str]:
    watched = set()
    for medium in media:
        watched.update(map(lambda p: p.file, medium.parts))
    return watched


def _map_path(path: str, path_mappings: Dict[str, str]) -> str:
    """Apply path mappings to convert a Plex path to a Jellyfin path."""
    for plex_path, jellyfin_path in path_mappings.items():
        if path.startswith(plex_path):
            return path.replace(plex_path, jellyfin_path, 1)
    return path


if __name__ == '__main__':
    migrate()

import requests
