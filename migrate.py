import requests
import click
from plexapi.server import PlexServer

@click.command()
@click.option('--secure/--insecure', help='Verify SSL')
@click.option('--plex-url', required=True, help='Plex server url')
@click.option('--plex-token', required=True, help='Plex token')
@click.option('--jellyfin-url', help='Jellyfin server url')
@click.option('--jellyfin-token', help='Jellyfin token')
def migrate(secure: bool, plex_url: str, plex_token: str, jellyfin_url: str,
    jellyfin_token: str):

    session = requests.Session()
    session.verify = secure
    plex = PlexServer(plex_url, plex_token, session=session)

    movies = plex.library.section('Films')
    for video in movies.search(unwatched=False):
        print(video.title)

    tvshows = plex.library.section('TV Shows')
    for show in tvshows.search(unwatched=False):
        for e in plex.library.section('TV Shows').get(show.title).episodes():
            if e.isWatched:
                print(e)


if __name__ == '__main__':
    migrate()
