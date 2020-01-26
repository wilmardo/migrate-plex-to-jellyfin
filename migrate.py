import requests
import urllib3
import click
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
@click.option('--secure/--insecure', help='Verify SSL')
@click.option('--plex-url', required=True, help='Plex server url')
@click.option('--plex-token', required=True, help='Plex token')
@click.option('--jellyfin-url', help='Jellyfin server url')
@click.option('--jellyfin-token', help='Jellyfin token')
def migrate(secure: bool, plex_url: str, plex_token: str, jellyfin_url: str,
    jellyfin_token: str):

    # Remove insecure request warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.verify = secure
    plex = PlexServer(plex_url, plex_token, session=session)

    jellyfin = JellyFinServer(url=jellyfin_url, api_key=jellyfin_token, session=session)

    plex_movies = plex.library.section('Films')
    watched_movies = []
    for video in plex_movies.search(unwatched=False):
        watched_movies.append(video.title)

    # plex_tvshows = plex.library.section('TV Shows')
    # plex_watched_episodes = []
    # for show in plex_tvshows.search(unwatched=False):
    #     for e in plex.library.section('TV Shows').get(show.title).episodes():
    #         if e.isWatched:
    #             plex_watched_episodes.append(e)

    # for u in jellyfin.get_users():
    #     search_result = jellyfin.search(user_id=u['id'], item_type='movie', query='Zero Days')
    #     if len(search_result) != 1:
    #         print('More then one match for {}')
    #         exit(1)
    #     else:
    #         jellyfin.mark_watched(user_id=u['id'], item_id=search_result[0]['Id'])

    for u in jellyfin.get_users():
        for m in watched_movies:
            search_result = jellyfin.search(user_id=u['id'], item_type='movie', query=m)
            if len(search_result) != 1:
                print(f'{bcolors.WARNING}{len(search_result)} matches for {m}{bcolors.ENDC}')
                # exit(1)
            else:
                jellyfin.mark_watched(user_id=u['id'], item_id=search_result[0]['Id'])
                print('marked {} as watched'.format(m))


if __name__ == '__main__':
    migrate()
