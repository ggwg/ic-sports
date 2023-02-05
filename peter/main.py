import network
import video

import asyncio
import cv2
import sys


async def h264_decode_worker(remote: network.Remote, decoder: video.VideoDec):
    while True:
        try:
            frame = await remote.get_h264_frame()
            decoder.write_h264(frame)
        except Exception as e:
            print("Error in decoding worker:", e)


async def video_transmitter_worker(remote: network.Remote, capture: video.VideoCap):
    while True:
        try:
            frame = await capture.read_h264_async()
            await remote.send_h264_frame(frame)
        except Exception as e:
            print("Error in transmitter worker:", e)


async def remote_render_worker(decoder: video.VideoDec):
    while True:
        try:
            frame = await decoder.read_raw_async()
            cv2.imshow("main", frame)
            cv2.waitKey(1)
        except Exception as e:
            print("Error in remote render worker:", e)


def get_remote(is_server):
    return network.Server() if is_server else network.Client()


async def main(is_server: bool):
    with video.VideoDec() as decoder:
        with video.VideoCap() as capture:
            async with get_remote(is_server) as remote:
                asyncio.create_task(h264_decode_worker(remote, decoder))
                asyncio.create_task(video_transmitter_worker(remote, capture))
                asyncio.create_task(remote_render_worker(decoder))

                await asyncio.Future()


if __name__ == "__main__":
    if sys.argv[1] == "server":
        asyncio.run(main(True))
    else:
        asyncio.run(main(False))
