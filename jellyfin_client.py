from typing import List, Optional
from dataclasses import dataclass

import requests


@dataclass
class JellyFinServer:
    url: str
    api_key: str
    session: requests.Session

    def _get(self, endpoint: str, payload: Optional[dict] = {}) -> dict:
        url = '{}/{}'.format(self.url, endpoint)
        payload['api_key'] = self.api_key
        r = self.session.get(
            url=url, params=payload, timeout=60)
        return r.json()

    def _post(self, endpoint, payload: Optional[dict] = {}) -> bool:
        payload['api_key'] = self.api_key
        r = self.session.post(
            url='{}/{}'.format(self.url, endpoint), params=payload, timeout=60)

    def get_users(self) -> List[dict]:
        """Get all Jellfin user

        Returns:
            List[dict]: List of dicts with usernames and ids
        """
        users = self._get(endpoint='Users')
        result = []
        for u in users:
            result.append({
                'name': u['Name'],
                'id': u['Id']
            })
        return result

    def get_user_id(self, name: str) -> str:
        """ Get user id by name

        Returns:
            str: user id
        """
        for u in self.get_users():
            if u['name'] == name:
                return u['id']

    def get_user_views(self, user_id: str) -> List:
        return self._get(endpoint='Users/{}/Views'.format(user_id))

    def get_all(self, user_id: str) -> List:
        """Get all items from JellyFin library

        Returns:
            List: List of results
        """
        results = []
        startIndex = 0
        while True:
            q = {
                'Recursive': True,
                'Fields': 'ProviderIds',
                'startIndex': startIndex,
                'Limit': 10,
                'includeItemTypes': 'Movie',
            }
            n = self._get(
                endpoint=f"Users/{user_id}/Items", payload=q)['Items']
            results += n
            startIndex += 10
            print(f"Fetched {startIndex} movies from jellyfin {[r['Name'] for r in results[-10:]]}")
            if len(n) == 0:
                break
        return results

    def search_by_provider(self, user_id: str, provider: str, item_id: str) -> List:
        """Search items by provider id

        Args:
            user_id (str): User id to get items for
            provider (str): provider (imdb, tvdb)

        Returns:
            List: List of results
        """
        q = {
            'IncludeItemTypes': item_type,
            'AnyProviderIdEquals': f"{provider}.{item_id}",
            'Recursive': True,
            'Fields': 'ProviderIds,UserData'
        }
        result = self._get(
            endpoint='Users/{}/Items'.format(user_id), payload=q)
        return result['Items']

    def mark_watched(self, user_id: str, item_id: str):
        """Mark item as watched

        Args:
            user_id (str): User to mark as watched
            item_id (str): itemId to mark as watched
        """
        self._post(endpoint='Users/{}/PlayedItems/{}'.format(user_id, item_id))
