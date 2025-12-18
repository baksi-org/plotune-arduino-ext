import asyncio
from plotune_sdk import PlotuneRuntime

from uuid import uuid4
from typing import Dict

from core.utils import get_config, get_custom_config
from core.io.forms import dynamic_arduino_form, form_dict_to_input
from core.io.stream_handler import ArduinoStreamHandler
from core.io.serial import SerialManager
from core.listener import ArduinoQueueListener

class ArduinoExtensionRunner:
    def __init__(self):
        self.config = get_config()
        self.custom_config = get_custom_config()

        self.serial_managers:Dict[str, SerialManager] = {}
        self.data_queues:Dict[str, asyncio.Queue] = {}
        self.error_queues:Dict[str, asyncio.Queue] = {}
        self.listener = ArduinoQueueListener()

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
        form = form_dict_to_input(data)
        _sm_id = uuid4().hex
        _sm = SerialManager(_sm_id, form)
        self.serial_managers[_sm_id] = _sm

        self.data_queues[_sm_id] = _sm.queue # TODO: Holding it for reference for gb, not sure if it is a good decision
        self.error_queues[_sm_id] = _sm.error_queue

        await _sm.start()

        self.listener.listen(
            _sm_id,
            _sm.queue,
            _sm.error_queue,
            data_handler=self.data_handler,
            error_handler=self.handle_error
        )

        return True


    async def data_handler(self, msg):
        print("here is the data",msg)

    async def handle_error(self, msg):
        print("here is the error",msg)


    def start(self):
        self.runtime.start()
    
