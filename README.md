# Migrate Plex to Jellyfin

WIP, project to migrate Plex watched statusses to Jellyfin :)

## Getting started

* Get plex token: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
* Get jellyfin token: Generate one under `Dashboard > API Keys`

Install requirements (in virtualenv):
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Command example:
```
python3 migrate.py --insecure --debug --plex-url https://plex.test.com:32400 --plex-token 123123123 --jellyfin-url https://jellyfin.test.com --jellyfin-token 123123123 --jellyfin-user user
```

```
Usage: migrate.py [OPTIONS]

Options:
  --plex-url TEXT        Plex server url  [required]
  --plex-token TEXT      Plex token  [required]
  --plex-movie-lib TEXT  Name of plex movie library
  --plex-tv-lib TEXT     Name of plex tv library
  --jellyfin-url TEXT    Jellyfin server url
  --jellyfin-token TEXT  Jellyfin token
  --jellyfin-user TEXT   Jellyfin user
  --secure / --insecure  Verify SSL
  --debug / --no-debug   Print more output
  --no-skip / --skip     Skip when no match it found instead of exiting
  --help                 Show this message and exit.
```