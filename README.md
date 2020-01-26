# Migrate Plex to Jellyfin

WIP, project to migrate Plex watched statusses to Jellyfin :)


## Generate jllyfin client

```
docker run --rm \
-v ${PWD}:/local openapitools/openapi-generator-cli generate \
-i /local/jellyfin-swagger.yml \
-g python-experimental \
-o /local/jellyfin-client \
--additional-properties=packageName=jellyfin_client
```
