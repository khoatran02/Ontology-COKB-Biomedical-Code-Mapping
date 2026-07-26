from typing import Any

import httpx


class FusekiUnavailableError(RuntimeError):
    pass


class FusekiRepository:
    def __init__(
        self,
        query_url: str,
        update_url: str,
        graph_store_url: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.query_url = query_url
        self.update_url = update_url
        self.graph_store_url = graph_store_url
        self.timeout = timeout_seconds

    async def ask(self, query: str) -> bool:
        response = await self._post_query(query)
        return bool(response.json()["boolean"])

    async def select(self, query: str) -> list[dict[str, Any]]:
        response = await self._post_query(query)
        payload = response.json()
        return payload.get("results", {}).get("bindings", [])

    async def construct(self, query: str) -> bytes:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.query_url,
                    data={"query": query},
                    headers={"accept": "text/turtle"},
                )
                response.raise_for_status()
                return response.content
            except httpx.HTTPError as exc:
                raise FusekiUnavailableError(str(exc)) from exc

    async def update(self, update: str) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(self.update_url, data={"update": update})
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise FusekiUnavailableError(str(exc)) from exc

    async def put_graph(self, graph_uri: str, rdf_bytes: bytes, content_type: str) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.put(
                    self.graph_store_url,
                    params={"graph": graph_uri},
                    content=rdf_bytes,
                    headers={"content-type": content_type},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise FusekiUnavailableError(str(exc)) from exc

    async def is_available(self) -> bool:
        try:
            await self.ask("ASK { ?s ?p ?o }")
            return True
        except (FusekiUnavailableError, KeyError, ValueError):
            return False

    async def _post_query(self, query: str) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.query_url,
                    data={"query": query},
                    headers={"accept": "application/sparql-results+json"},
                )
                response.raise_for_status()
                return response
            except httpx.HTTPError as exc:
                raise FusekiUnavailableError(str(exc)) from exc
