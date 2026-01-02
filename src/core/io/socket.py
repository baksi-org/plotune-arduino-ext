# core/io/socket.py
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from typing import Any


class SocketHandler:
    def __init__(self, runner):
        self.runner = runner
        self.active = False

    async def stream(self, signal_name: str, websocket: WebSocket, data: Any):
        q: asyncio.Queue = asyncio.Queue()

        async def listen(sm_id, msg):
            payload = {"timestamp": msg.get("time"), "value": msg.get("value")}
            await q.put(payload)

        # register listen handler
        await self.runner.subscribe(signal_name, listen)
        print(f"{signal_name} requested, subscribed listener")

        try:
            while True:
                try:
                    payload = await q.get()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    print("queue get error:", exc)
                    continue

                # send payload to websocket (runtime already accepted WS)
                try:
                    await websocket.send_json(payload)
                except WebSocketDisconnect:
                    raise
                except Exception as exc:
                    print("websocket send error:", exc)
                    # break and cleanup
                    break

                await asyncio.sleep(0.03)

        except WebSocketDisconnect:
            print(f"Client disconnected from {signal_name}")
        finally:
            # always unsubscribe the listener to avoid leaks
            await self.runner.unsubscribe(signal_name, listen)
            print(f"Unsubscribed listener for {signal_name}")
