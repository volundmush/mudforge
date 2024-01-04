import logging
import traceback
from ..core import Core


class PortalCore(Core):
    app = "portal"

    async def handle_new_protocol(self, protocol):
        protocol.core = self
        try:
            self.game_sessions[protocol.capabilities.session_name] = protocol
            await protocol.run()
        except Exception as err:
            logging.error(traceback.format_exc())
            logging.error(err)
        finally:
            del self.game_sessions[protocol.capabilities.session_name]
