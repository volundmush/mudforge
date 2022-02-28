from rich.ansi import AnsiDecoder
from .base import BaseProcessor


class RawProcessor(BaseProcessor):
    decoder = AnsiDecoder()

    async def process(self, conn, body):
        for entry in body:
            for line in self.decoder.decode(entry.get("data", "")):
                await conn.send_text_data("line", conn.print(line))
