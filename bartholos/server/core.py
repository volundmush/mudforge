import bartholos
import logging
import traceback

from bartholos.core import Core


class ServerCore(Core):
    app = "server"

    async def handle_new_client(self, ws, data):
        game_sess_class = bartholos.CLASSES["game_session"]
        sess = game_sess_class(ws, data)
        sess_name = data.capabilities.session_name
        sess.core = self

        try:
            self.game_sessions[sess_name] = sess
            await sess.run()
        except Exception as err:
            logging.error(traceback.format_exc())
            logging.error(err)
        finally:
            del self.game_sessions[sess_name]
