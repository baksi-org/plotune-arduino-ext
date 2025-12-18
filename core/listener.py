import asyncio
from typing import Dict, Any, Union, Callable, Awaitable

HandlerType = Union[Callable[[Dict[str, Any]], None], Callable[[Dict[str, Any]], Awaitable[None]]]

class ArduinoQueueListener:
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}

    def listen(
        self,
        sm_id: str,
        data_queue: asyncio.Queue,
        error_queue: asyncio.Queue,
        data_handler: HandlerType,
        error_handler: HandlerType,
        loop: asyncio.AbstractEventLoop = None
    ):
        loop = loop or asyncio.get_event_loop()

        async def _data_loop():
            while True:
                msg = await data_queue.get()
                if msg is None:
                    break
                if asyncio.iscoroutinefunction(data_handler):
                    await data_handler(sm_id, msg)
                else:
                    data_handler(sm_id, msg)

        async def _error_loop():
            while True:
                err = await error_queue.get()
                if err is None:
                    break
                if asyncio.iscoroutinefunction(error_handler):
                    await error_handler(sm_id, err)
                else:
                    error_handler(sm_id, err)

        self.tasks[sm_id] = loop.create_task(_data_loop())
        self.tasks[f"{sm_id}_err"] = loop.create_task(_error_loop())

    def stop(self, sm_id: str):
        if sm_id in self.tasks:
            self.tasks[sm_id].cancel()
            self.tasks.pop(sm_id, None)
        if f"{sm_id}_err" in self.tasks:
            self.tasks[f"{sm_id}_err"].cancel()
            self.tasks.pop(f"{sm_id}_err", None)
