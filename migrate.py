#!/bin/python3

from typing import List, Optional

import requests
import urllib3
import click
import re
import sys
import pickle

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

agents_movies = [
    {"plex": "themoviedb", "jellyfin": "Tmdb"},
    {"plex": "imdb", "jellyfin": "Imdb"},
]

def _jellyfin_agent_from_plex(plex_agent_name: str) -> Optional[str]:
    for a in agents_movies:
        if a['plex'] == plex_agent_name:
            return a['jellyfin']
    return None


@click.command()
@click.option('--plex-url', required=True, help='Plex server url')
@click.option('--plex-token', required=True, help='Plex token')
@click.option('--jellyfin-url', help='Jellyfin server url')
@click.option('--jellyfin-token', help='Jellyfin token')
@click.option('--jellyfin-user', help='Jellyfin user')
@click.option('--secure/--insecure', help='Verify SSL')
@click.option('--debug/--no-debug', help='Print more output')
@click.option('--dry-run/--no-dry-run', help='Verify SSL', default=False)
@click.option('--plex-movie-lib', required=True, help='Name of Plex movie library')
def migrate(plex_url: str, plex_token: str, jellyfin_url: str,
            jellyfin_token: str, jellyfin_user: str,
            secure: bool, debug: bool, dry_run: bool,
            plex_movie_lib: str):

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

    try:
        with open('cache_plex.pkl', 'rb') as f:
            plex_watched = pickle.load(f)
    except Exception:
        # Get all Plex watched movies
        if plex_movie_lib is not None:
            plex_movies = plex.library.section(plex_movie_lib)
            for m in plex_movies.search(unwatched=False):
                infos = []
                for agent in agents_movies:
                    # Take only the first result of each agent
                    agent_matches = m.matches(agent=agent['plex'])
                    if len(agent_matches) == 0:
                        continue
                    best_agent_match = agent_matches[0]
                    info = _extract_provider(guid=best_agent_match.guid)
                    info['agent_title'] = best_agent_match.name
                    info['original_title'] = m.title
                    infos.append(info)

                if len(infos) == 0:
                    print(f"{bcolors.WARNING}No match for plex item {m.title}{bcolors.ENDC}")
                    continue
                else:
                    infos_str = infos[0]['original_title'] + " ->"
                    for info in infos:
                        infos_str += f" {info['provider']}:{info['item_id']} {info['agent_title']}"
                    print(f"{bcolors.OKGREEN}Matches for {m.title}: {infos_str}{bcolors.ENDC}")

                plex_watched.append(infos)

        with open('cache_plex.pkl', 'wb') as f:
            pickle.dump(plex_watched, f)

        

    # This gets all jellyfin movies since filtering on provider id isn't supported:
    # https://github.com/jellyfin/jellyfin/issues/1990
    jf_uid = jellyfin.get_user_id(name=jellyfin_user)

    try:
        with open('cache_jellyfin.pkl', 'rb') as f:
            jf_library = pickle.load(f)
    except Exception:
        jf_library = jellyfin.get_all(user_id=jf_uid)
        with open('cache_jellyfin.pkl', 'wb') as f:
            pickle.dump(jf_library, f)

    for watched in plex_watched:
        # print(f"Searching for {watched[0]['original_title']} in {len(jf_library)} items.")
        search_result = _search(jf_library, watched)
        if search_result and not search_result['UserData']['Played']:
            if not dry_run:
                jellyfin.mark_watched(
                    user_id=jf_uid, item_id=search_result['Id'])
            print(f"{bcolors.OKGREEN}Marked {watched[0]['original_title']} as watched{bcolors.ENDC}")
        elif not search_result:
            print(f"{bcolors.WARNING}No matches for {watched[0]['original_title']}{bcolors.ENDC}")
        else:
            if debug:
                print(f"{bcolors.OKBLUE}{watched[0]['original_title']} already marked as watched{bcolors.ENDC}")

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
        for provider in item:
            if data['ProviderIds'].get(_jellyfin_agent_from_plex(provider['provider'])) == provider['item_id']:
                return data
    return None


def _extract_provider(guid: str) -> dict:
    """Extract Plex provider and return JellyFin compatible data

    Args:
        data (dict): movie guid

    Returns:
        dict: provider in plex format and item_id as identifier
    """
    result = {}

    # example: 'com.plexapp.agents.imdb://tt1068680?lang=en'
    match = re.match('com\.plexapp\.agents\.(.*):\/\/(.*)\?', guid)

    if match:
        result = {
            'provider': match.group(1),
            'item_id': match.group(2)
        }

    return result


if __name__ == '__main__':
    migrate()

