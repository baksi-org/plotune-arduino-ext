from plotune_sdk import PlotuneRuntime


from core.utils import get_config, get_custom_config
from core.io.forms import dynamic_arduino_form
from core.io.stream_handler import ArduinoStreamHandler

class ArduinoExtensionRunner:
    def __init__(self):
        self.config = get_config()
        self.custom_config = get_custom_config()

        self.runtime = None

        self._get_runtime()
        self._init_services()
        self._register_events()

    def _init_services(self):
        self.stream_handler = ArduinoStreamHandler(
            serial_manager=None
        )
        
    def _get_runtime(self):
        if self.runtime:
            return self.runtime

        connection = self.config.get("connection", {})
        self.core_url = f"http://{connection.get('target', '127.0.0.1')}:{connection.get('target_port', '8000')}"

        self.runtime = PlotuneRuntime(
            ext_name=self.config.get("id"),
            core_url=self.core_url,
            config=self.config,
        )
        return self.runtime

    def _register_events(self):
        """
        Register runtime events AFTER runtime initialization.
        """
        self.runtime.server.on_event("/form")(self._handle_form)
        self.runtime.server.on_event("/form", method="POST")(self._new_connection)

    def _build_routes(self):
        _server = self.runtime.server
        
        async def connect_request(payload:dict):
            print(payload)

        _server.route("/connect",method="POST")(connect_request)

    async def _handle_form(self, data: dict):
        return dynamic_arduino_form()
    
    async def _new_connection(self, data:dict):
        print(data)
        return 200

    def start(self):
        self.runtime.start()
