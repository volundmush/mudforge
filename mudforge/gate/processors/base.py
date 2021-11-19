

class BaseProcessor:

    def __init__(self, app):
        self.app = app

    def setup(self):
        pass

    async def process(self, conn, body):
        pass
