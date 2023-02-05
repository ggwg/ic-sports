import json
import websockets
import asyncio


class Busy(Exception):
    pass


class Remote:
    def __init__(self) -> None:
        self.remote = None
        self.h264_queue = asyncio.Queue(10)
        self.ctrl_queue = asyncio.Queue(0)
        print("super init")

    async def handle(self, websocket):
        if self.remote:
            raise Busy

        self.remote = websocket

        try:
            async for msg in websocket:
                if isinstance(msg, bytes):
                    # H264 stream
                    await self.h264_queue.put_nowait(msg)
                else:
                    # Control message
                    msg = json.loads(msg)
                    await self.ctrl_queue.put(msg)
        finally:
            self.remote = None

    async def get_h264_frame(self):
        return await self.h264_queue.get()

    async def send_h264_frame(self, data: bytes):
        if self.remote:
            await self.remote.send(data)

    async def send_control(self, data: dict):
        if self.remote:
            await self.remote.send(json.dumps(data))

    async def recv_control(self):
        return await self.ctrl_queue.get()


class Server(Remote):
    def __init__(self, port: int = 8765) -> None:
        super().__init__()
        self.port = port
        self.server = websockets.serve(self.__server_handle, "0.0.0.0", port)

    async def __server_handle(self, websocket):
        print("new connection")
        try:
            await self.handle(websocket)
        except Busy:
            await websocket.send(json.dumps({"status": "busy"}))

    async def __aenter__(self):
        print(f"Server listening on {self.port}")
        await self.server.__aenter__()
        print("done")
        return self

    async def __aexit__(self, a, b, c):
        await self.server.__aexit__(a, b, c)


class Client(Remote):
    def __init__(self, url="ws://localhost:8765") -> None:
        super().__init__()
        self.client = websockets.connect(url)

    async def __aenter__(self):
        websocket = await self.client.__aenter__()
        self.task = asyncio.create_task(self.handle(websocket))
        return self

    async def __aexit__(self, a, b, c):
        await self.task
        await self.client.__aexit__(a, b, c)


if __name__ == "__main__":
    async def main():
        async with Server() as server:
            ctrl = await server.recv_control()
            print(ctrl)

    import asyncio
    asyncio.run(main())
