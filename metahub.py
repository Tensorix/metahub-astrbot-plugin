import requests

class MetaHub:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()
    
    def post_message(self, data:dict):
        url = f"{self.base_url}/experimental/events/ping"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = self.session.post(url, json=data, headers=headers)
        return response.json()