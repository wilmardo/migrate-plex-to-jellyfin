from typing import List, Optional
from dataclasses import dataclass

import requests

@dataclass
class JellyFinServer:
    url: str
    api_key: str
    session: requests.Session

    def _get(self, endpoint: str, payload: Optional[dict] = {}) -> dict:
        payload['api_key'] = self.api_key
        r = self.session.get(url='{}/{}'.format(self.url, endpoint), params=payload)
        return r.json()

    def _post(self, endpoint, payload: Optional[dict] = {}) -> bool:
        payload['api_key'] = self.api_key
        r = self.session.post(url='{}/{}'.format(self.url, endpoint), params=payload)

    def get_users(self) -> List[dict]:
        users = self._get(endpoint='Users')
        result = []
        for u in users:
            result.append({
              'name': u['Name'],
              'id': u['Id']
            })
        return result

    def get_user_views(self, user_id: str) -> List:
        return self._get(endpoint='Users/{}/Views'.format(user_id))

    def search(self, user_id: str, item_type: str, query: str) -> List:
        q = {
            'searchterm': query,
            'IncludeItemTypes': item_type,
            'recursive': True
        }
        result = self._get(endpoint='Users/{}/Items'.format(user_id), payload=q)
        return result['Items']

    def mark_watched(self, user_id: str, item_id: str):
        self._post(endpoint='Users/{}/PlayedItems/{}'.format(user_id, item_id))
