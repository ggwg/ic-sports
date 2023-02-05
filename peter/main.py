import network
import video

import asyncio
import cv2
import sys
from contextlib import suppress
from typing import Sequence

async def h264_decode_worker(remote: network.Remote, decoder: video.VideoDec):
    while True:
        try:
            frame = await remote.get_h264_frame()
            decoder.write_h264(frame)
        except Exception as e:
            print("Error in decoding worker:", e)


async def video_transmitter_worker(remote: network.Remote, encoder: video.VideoEnc):
    while True:
        try:
            frame = await encoder.read_h264_async()
            print("got h264 frame")
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

async def h264_encode_worker(queue: asyncio.Queue, encoder: video.VideoEnc):
    while True:
        try:
            frame = await queue.get()
            encoder.write_raw(frame)
        except Exception as e:
            print("Error in encoding worker:", e)

async def frame_queue_tee(capture: video.VideoCap, queues: Sequence[asyncio.Queue]):
    while True:
        try:
            frame = await capture.read_raw_async()
            for queue in queues:
                with suppress(asyncio.queues.QueueFull):
                    queue.put_nowait(frame)
        except Exception as e:
            print("Error in frame tee:", e)

async def main():
    if sys.argv[1] == "client":
        remote = network.Client(sys.argv[2])
    else:
        remote = network.Server()
    
    encoder = video.VideoEnc()
    frame_queue = asyncio.Queue(1)
    frame_queue_2 = asyncio.Queue(1)

    with video.VideoDec() as decoder:
        print("videodec init done")
        with video.VideoCap() as capture:
            print("videocap init done")
            remote.conn_on_cb = lambda _: encoder.run()
            remote.conn_off_cb = lambda _: encoder.stop()
            async with remote:
                print("starting")
                asyncio.create_task(h264_decode_worker(remote, decoder))
                asyncio.create_task(video_transmitter_worker(remote, encoder))
                asyncio.create_task(remote_render_worker(decoder))
                asyncio.create_task(h264_encode_worker(frame_queue, encoder))
                asyncio.create_task(frame_queue_tee(capture, (frame_queue, frame_queue_2)))

                while True:
                    frame = await frame_queue_2.get()

                    cv2.imshow("local", frame)
                    cv2.waitKey(1)

                await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
