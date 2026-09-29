import asyncio

from fastapi import WebSocket

from server.config import VALID_PEOPLE


connected_clients: set[WebSocket] = set()
connected_clients_by_person: dict[str, set[WebSocket]] = {person: set() for person in VALID_PEOPLE}
active_call_routes: dict[str, dict[str, WebSocket]] = {}
broadcast_lock = asyncio.Lock()


async def broadcast(message: dict):
    async with broadcast_lock:
        clients = list(connected_clients)
        results = await asyncio.gather(
            *(client.send_json(message) for client in clients), return_exceptions=True
        )
        for client, result in zip(clients, results):
            if isinstance(result, Exception):
                connected_clients.discard(client)
                for person_clients in connected_clients_by_person.values():
                    person_clients.discard(client)
