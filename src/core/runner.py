import asyncio
from plotune_sdk import PlotuneRuntime

from time import time
from uuid import uuid4
from typing import Dict, Optional, List

from core.utils import get_config, get_custom_config
from core.io.forms import dynamic_arduino_form, form_dict_to_input
from core.io.stream_handler import ArduinoStreamHandler
from core.io.serial import SerialManager
from core.listener import ArduinoQueueListener, HandlerType
from core.io.socket import SocketHandler


class ArduinoExtensionRunner:
    def __init__(self):
        self.config = get_config()
        self.custom_config = get_custom_config()

        self.serial_managers: Dict[str, SerialManager] = {}
        self.data_queues: Dict[str, asyncio.Queue] = {}
        self.error_queues: Dict[str, asyncio.Queue] = {}
        self.subscribers: Dict[str, List[HandlerType]] = {}

        self.listener = ArduinoQueueListener()
        self.socket = SocketHandler(self)

        self.signals: Dict[str, Dict[str, str]] = {}
        self.index_sm: Dict[str, int] = {}
        self._last_index = 0

        self._runtime: Optional[PlotuneRuntime] = None
        self._core_url: Optional[str] = None

        self._init_services()
        self._register_events()

    async def subscribe(self, key: str, handler: HandlerType):
        print("Subscribed", key, handler)
        self.subscribers.setdefault(key, []).append(handler)

    async def unsubscribe(self, key: str, handler: HandlerType) -> None:
        """Unregister a previously registered handler."""
        lst = self.subscribers.get(key)
        if not lst:
            return
        try:
            lst.remove(handler)
        except ValueError:
            pass
        if not lst:
            self.subscribers.pop(key, None)

    def _init_services(self):
        self.stream_handler = ArduinoStreamHandler(serial_manager=None)

    @property
    def runtime(self) -> PlotuneRuntime:
        if self._runtime:
            return self._runtime
        connection = self.config.get("connection", {})
        target = connection.get("target", "127.0.0.1")
        port = connection.get("target_port", "8000")
        _core_url = f"http://{target}:{port}"
        self._runtime = PlotuneRuntime(
            ext_name=self.config.get("id"),
            core_url=_core_url,
            config=self.config,
        )
        return self._runtime

    def _register_events(self):
        """
        Register runtime events AFTER runtime initialization.
        """
        self.runtime.server.on_event("/form")(self._handle_form)
        self.runtime.server.on_event("/form", method="POST")(self._new_connection)

    def _build_routes(self):
        _server = self.runtime.server

        async def connect_request(payload: dict):
            print(payload)

        _server.route("/connect", method="POST")(connect_request)

    async def _handle_form(self, data: dict):
        return dynamic_arduino_form()

    async def _new_connection(self, data: dict):
        from serial import SerialException

        form = form_dict_to_input(data)
        _sm_id = uuid4().hex[:6]
        try:
            _sm = SerialManager(_sm_id, form)
            self.serial_managers[_sm_id] = _sm

            self.data_queues[_sm_id] = (
                _sm.queue
            )  # TODO: Holding it for reference for gb, not sure if it is a good decision
            self.error_queues[_sm_id] = _sm.error_queue

            await _sm.start()

            self.listener.listen(
                _sm_id,
                _sm.queue,
                _sm.error_queue,
                data_handler=self.data_handler,
                error_handler=self.handle_error,
            )

            self.index_sm[_sm_id] = self._last_index
            self._last_index += 1

            # Registering an handler
            if not self.socket.active:
                self.runtime.server.on_ws()(self.socket.stream)
                self.socket.active = True
                print("Stream handler registered")

            await self.runtime.core_client.toast(
                "Arduino",
                "New arduino connection requested, please await for signals to populate",
                duration=2500,
            )

            return True
        except SerialException as exc:

            await self.runtime.core_client.toast(
                "Arduino",
                f"{form.serial_port} is already used or cannot connect",
                duration=5000,
            )
            return False

    def unique_naming(self, sm_id: str, key: str):
        i = self.index_sm[sm_id]
        if i == 0:
            return key
        return f"{key}[{i}]"

    async def check_signal(self, sm_id: str, msg: dict):
        _key = msg.get("key")

        if sm_id not in self.signals:
            self.signals[sm_id] = {}

        sm_signals = self.signals[sm_id]

        if _key not in sm_signals:
            unique_key = self.unique_naming(sm_id, _key)
            sm_signals[_key] = unique_key

            print(f"New Variable {_key} -> {unique_key}")

            await self.runtime.core_client.add_variable(
                variable_name=unique_key,
                variable_desc=f"{sm_id}",
            )
        else:
            unique_key = sm_signals[_key]

        return unique_key

    async def data_handler(self, sm_id: str, msg: dict) -> None:
        """Called by the queue listener when a new parsed message arrives.

        This dispatches to handlers registered for:
        - the raw/base key (e.g. "temperature")
        - the unique key (e.g. "temperature[1]") if created
        """
        base_key = msg.get("key")
        if base_key is None:
            return

        unique_key = await self.check_signal(sm_id, msg)

        # gather handlers for both the base key and the unique_key
        handlers = []
        handlers.extend(self.subscribers.get(base_key, []))
        if unique_key and unique_key != base_key:
            handlers.extend(self.subscribers.get(unique_key, []))

        if not handlers:
            return

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(sm_id, msg)
                else:
                    # run sync handler in loop to avoid blocking if necessary
                    handler(sm_id, msg)
            except Exception as exc:
                # don't crash dispatcher; log to error queue or console
                print(f"handler error for {base_key}: {exc}")

    async def handle_error(self, sm_id: str, msg: dict):
        _type = msg.get("type")
        _line = msg.get("line")
        if not _type or not _line:
            print(msg)
            return
        print(f"{sm_id} | {_type}\t{_line}")

    def start(self):
        self.runtime.start()
