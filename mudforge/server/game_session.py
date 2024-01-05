import pickle
import logging
import traceback

from mudforge.game_session import (
    GameSession as BaseGameSession,
    ClientHello,
    ClientCommand,
    ClientUpdate,
    ClientDisconnect,
    ServerDisconnect,
    ServerSendables,
    ServerUserdata,
    Sendable,
    ServerMSSP,
)


class GameSession(BaseGameSession):
    def __init__(self, ws, data: ClientHello):
        super().__init__()
        self.capabilities = data.capabilities
        self.userdata = data.userdata
        self.ws = ws

    async def run(self):
        await self.start()
        async with self.task_group as tg:
            self.tasks["reader"] = tg.create_task(self.run_reader())
            self.tasks["writer"] = tg.create_task(self.run_writer())
            self.run_extend()

    def run_extend(self):
        """
        Use this to add anything else needed to the starting Task Group.
        """

    async def run_writer(self):
        while data := await self.outgoing_queue.get():
            try:
                await self.ws.send(pickle.dumps(data))
            except Exception as err:
                logging.error(traceback.format_exc())
                logging.error(err)

    async def run_reader(self):
        async for message in self.ws:
            match message:
                case bytes():
                    msg = pickle.loads(message)
                    await self.handle_incoming_message(msg)
                case str():
                    pass

    async def handle_incoming_message(self, msg):
        match msg:
            case ClientHello():
                # This shouldn't happen, but we'll handle it anyways.
                await self.handle_incoming_hello(msg)
            case ClientCommand():
                await self.handle_incoming_command(msg)
            case ClientUpdate():
                await self.handle_incoming_update(msg)
            case ClientDisconnect():
                await self.handle_incoming_disconnect(msg)
            case ClientUpdate():
                await self.handle_incoming_update(msg)
            case _:
                await self.handle_incoming_other(msg)

    async def handle_incoming_hello(self, msg: ClientHello):
        self.capabilities = msg.capabilities
        self.userdata = msg.userdata

    async def handle_incoming_command(self, msg: ClientCommand):
        out = ServerSendables()
        m = Sendable()
        m.add_renderable(f"ECHO: {msg.text}")
        out.add_sendable(m)
        await self.outgoing_queue.put(out)

    async def handle_incoming_update(self, msg: ClientUpdate):
        for k, v in msg.capabilities.items():
            setattr(self.capabilities, k, v)
            await self.at_capability_change(k, v)

    async def at_capability_change(self, capability: str, value):
        pass

    async def handle_incoming_disconnect(self, msg: ClientDisconnect):
        pass

    async def handle_incoming_other(self, msg):
        pass

    async def start(self):
        if self.userdata:
            await self.start_resume()
        else:
            await self.start_fresh()

    async def start_resume(self):
        out = ServerSendables()
        msg = Sendable()
        msg.add_renderable("Welcome back to the game!")
        out.add_sendable(msg)
        await self.outgoing_queue.put(out)

    async def start_fresh(self):
        out = ServerSendables()
        msg = Sendable()
        msg.add_renderable("Welcome to the game!")
        out.add_sendable(msg)
        await self.outgoing_queue.put(out)
