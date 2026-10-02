import asyncio
from collections import defaultdict

from fastapi import WebSocket

connected_clients: set[WebSocket] = set()
connected_clients_by_person: dict[str, set[WebSocket]] = defaultdict(set)
connected_clients_by_conversation: dict[str, set[WebSocket]] = defaultdict(set)
websocket_conversations: dict[WebSocket, str] = {}
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
                for conversation_clients in connected_clients_by_conversation.values():
                    conversation_clients.discard(client)
                websocket_conversations.pop(client, None)


async def broadcast_to_conversation(conversation_id: str, message: dict):
    async with broadcast_lock:
        clients = list(connected_clients_by_conversation[conversation_id])
        results = await asyncio.gather(
            *(client.send_json(message) for client in clients), return_exceptions=True
        )
        for client, result in zip(clients, results):
            if isinstance(result, Exception):
                connected_clients.discard(client)
                for person_clients in connected_clients_by_person.values():
                    person_clients.discard(client)
                connected_clients_by_conversation[conversation_id].discard(client)
                websocket_conversations.pop(client, None)
