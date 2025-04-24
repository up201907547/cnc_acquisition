import asyncio
import websockets
import json
import threading
import time
import datetime

class GrafanaLiveStreamer:
    def __init__(self, uri="ws://localhost:3000/api/live/push/custom/my-channel"):
        self.uri = uri
        self.ws = None
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self._start_loop, daemon=True).start()

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _connect(self):
        try:
            self.ws = await websockets.connect(self.uri)
        except Exception as e:
            print(f"[LiveStreamer] Connection failed: {e}")
            self.ws = None

    def send(self, data_time_ns, data_dict):
        async def _send():
            try:
                if not self.ws or self.ws.closed:
                    await self._connect()

                # Convert nanoseconds to ISO format for Grafana
                dt = data_time_ns

                message = {
                    "time": dt,
                    "fields": data_dict
                }

                await self.ws.send(json.dumps(message))

            except Exception as e:
                print(f"[LiveStreamer] Error: {e}")
                self.ws = None  # Trigger reconnect on next send

        asyncio.run_coroutine_threadsafe(_send(), self.loop)

    def close(self):
        if self.ws:
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)