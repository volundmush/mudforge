import logging
from mudforge.app import MudApp
from mudforge.shared import ConnectionOutMessage, ConnectionOutMessageType
from .link import LinkManager


class MudForge(MudApp):
    """
    The core of MudForge.
    """
    app_name = 'mudforge'

    async def configure(self):
        self.link = LinkManager(self, f"ws://{self.shared['interfaces']['internal']}:{self.shared['link']}")
        self.running_services.append(self.link)

    async def register_connection(self, details):
        conn = self.classes["connection"](self, details)
        self.game_clients[details.client_id] = conn
        logging.info(f"Connection {details.client_id} registered. Protocol: {details.protocol}. Host IP: {details.host_address}. Client: {details.client_name} {details.client_version}")
        await conn.on_connect()

    async def remove_connection(self, client_id: str, reason: str, inform_gate: bool):
        if (conn := self.game_clients.get(client_id, None)):
            logging.info(f"Disconnecting client {client_id} because: {reason}")
            await conn.on_disconnect(reason)
            if inform_gate:
                msg = ConnectionOutMessage(msg_type=ConnectionOutMessageType.DISCONNECT, client_id=client_id, data=None)
                await self.link.inbox.put(msg)
            self.game_clients.pop(client_id, None)
