from typing import List

import requests
import urllib3
import click
import re
import sys

from plexapi.server import PlexServer
from jellyfin_client import JellyFinServer


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


@click.command()
@click.option('--plex-url', required=True, help='Plex server url')
@click.option('--plex-token', required=True, help='Plex token')
@click.option('--jellyfin-url', help='Jellyfin server url')
@click.option('--jellyfin-token', help='Jellyfin token')
@click.option('--jellyfin-user', help='Jellyfin user')
@click.option('--secure/--insecure', help='Verify SSL')
@click.option('--debug/--no-debug', help='Print more output')
@click.option('--no-skip/--skip', help='Skip when no match it found instead of exiting')
@click.option('--plex-tv-lib', default='TV Shows', help='Name of Plex TV library')
@click.option('--plex-movie-lib', default='Films', help='Name of Plex movie library')
def migrate(plex_url: str, plex_token: str, jellyfin_url: str,
            jellyfin_token: str, jellyfin_user: str,
            secure: bool, debug: bool, no_skip: bool,
            plex_tv_lib: str, plex_movie_lib: str):

    # Remove insecure request warnings
    if not secure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Setup sessions
    session = requests.Session()
    session.verify = secure
    plex = PlexServer(plex_url, plex_token, session=session)

    jellyfin = JellyFinServer(
        url=jellyfin_url, api_key=jellyfin_token, session=session)

    # Watched list from Plex
    plex_watched = []

    # Get all Plex watched movies
    # TODO: remove harcoded library name
    plex_movies = plex.library.section(plex_movie_lib)
    for m in plex_movies.search(unwatched=False):
        info = _extract_provider(data=m.guid)

        if not info:
            print(f"{bcolors.WARNING}No provider match in {m.guid} for {m.title}{bcolors.ENDC}")
            if no_skip:
                sys.exit(1)
            else:
                continue

        info['title'] = m.title
        plex_watched.append(info)

    # Get all Plex watched episodes
    plex_tvshows = plex.library.section(plex_tv_lib)
    plex_watched_episodes = []
    for show in plex_tvshows.search(**{"episode.unwatched": False}):
        for e in plex.library.section(plex_tv_lib).get(show.title).episodes():
            info = _extract_provider(data=e.guid)
            
            # TODO: feels copy paste of above, move to function
            if not info:
                print(f"{bcolors.WARNING}No provider match in {e.guid} for {show.title} {e.seasonEpisode.capitalize()} {bcolors.ENDC}")
                if no_skip:
                    sys.exit(1)
                else:
                    continue

            info['title'] = f"{show.title} {e.seasonEpisode.capitalize()} {e.title}"  # s01e03 > S01E03
            plex_watched.append(info)

    # This gets all jellyfin movies since filtering on provider id isn't supported:
    # https://github.com/jellyfin/jellyfin/issues/1990
    jf_uid = jellyfin.get_user_id(name=jellyfin_user)
    jf_library = jellyfin.get_all(user_id=jf_uid)

    for watched in plex_watched:
        search_result = _search(jf_library, watched)
        if search_result and not search_result['UserData']['Played']:
            jellyfin.mark_watched(
                user_id=jf_uid, item_id=search_result['Id'])
            print(f"{bcolors.OKGREEN}Marked {watched['title']} as watched{bcolors.ENDC}")
        elif not search_result:
            print(f"{bcolors.WARNING}No matches for {watched['title']}{bcolors.ENDC}")
            if no_skip:
                sys.exit(1)
        else:
            if debug:
                print(f"{bcolors.OKBLUE}{watched['title']}{bcolors.ENDC}")

    print(f"{bcolors.OKGREEN}Succesfully migrated {len(plex_watched)} items{bcolors.ENDC}")


def _search(lib_data: dict, item: dict) -> List:
    """Search for plex item in jellyfin library

    Args:
        lib_data (dict): jellyfin lib as returned by client
        item (dict): Plex item

    Returns:
        List: [description]
    """
    for data in lib_data:
        if data['ProviderIds'].get(item['provider']) == item['item_id']:
            return data


def _extract_provider(data: dict) -> dict:
    """Extract Plex provider and return JellyFin compatible data

    Args:
        data (dict): plex episode or movie guid

    Returns:
        dict: provider in JellyFin format and item_id as identifier
    """
    result = {}

    # example: 'com.plexapp.agents.imdb://tt1068680?lang=en'
    # example: 'com.plexapp.agents.thetvdb://248741/1/1?lang=en'
    match = re.match('com\.plexapp\.agents\.(.*):\/\/(.*)\?', data)

    if match:
        result = {
            'provider': match.group(1).replace('the', '').capitalize(),  # Jellyfin uses Imdb and Tvdb
            'item_id': match.group(2)
        }

    return result


if __name__ == '__main__':
    migrate()
