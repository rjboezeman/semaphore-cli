import requests


class SemaphoreClient:
    """Thin wrapper around requests.Session for the SemaphoreUI API."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._session = requests.Session()

    def __enter__(self) -> "SemaphoreClient":
        return self

    def __exit__(self, *args: object) -> None:
        self._session.close()

    def login(self) -> None:
        """Authenticate and store the session cookie."""
        r = self._session.post(
            f"{self.base_url}/api/auth/login",
            json={"auth": self._username, "password": self._password},
        )
        r.raise_for_status()

    def get(self, path: str) -> list | dict:
        r = self._session.get(f"{self.base_url}{path}")
        r.raise_for_status()
        return r.json()

    def post(self, path: str, payload: dict) -> dict:
        r = self._session.post(f"{self.base_url}{path}", json=payload)
        if not r.ok:
            raise RuntimeError(f"POST {path} failed [{r.status_code}]: {r.text}")
        return r.json()

    def put(self, path: str, payload: dict) -> None:
        r = self._session.put(f"{self.base_url}{path}", json=payload)
        if not r.ok:
            raise RuntimeError(f"PUT {path} failed [{r.status_code}]: {r.text}")

    def delete(self, path: str) -> None:
        r = self._session.delete(f"{self.base_url}{path}")
        if not r.ok:
            raise RuntimeError(f"DELETE {path} failed [{r.status_code}]: {r.text}")
