import asyncio
from time import time


class ArduinoStreamHandler:
    def __init__(self, serial_manager):
        self.serial_manager = serial_manager

    async def handle(self, signal_name, websocket, _):
        print(f"[WS] Signal requested: {signal_name}")

        try:
            async for packet in self.serial_manager.stream():
                await websocket.send_json(packet)
        except Exception as e:
            print(f"[WS] stream closed: {e}")
