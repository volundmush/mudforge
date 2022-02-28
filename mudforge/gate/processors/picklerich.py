import pickle
from .base import BaseProcessor


class PickleRichProcessor(BaseProcessor):

    async def process(self, conn, body):
        for entry in body:
            message = pickle.loads(bytes(entry.get("data", b'')))
            out_data = conn.print(message)
            await conn.send_text_data(entry.get("mode", "line"), out_data)
