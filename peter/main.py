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



async def main():
    if sys.argv[1] == "client":
        remote = network.Client(sys.argv[2])
    else:
        remote = network.Server()

    with video.VideoDec() as decoder:
        print("videodec init done")
        with video.VideoCap() as capture:
            print("videocap init done")
            async with remote:
                print("starting")
                asyncio.create_task(h264_decode_worker(remote, decoder))
                asyncio.create_task(video_transmitter_worker(remote, capture))
                asyncio.create_task(remote_render_worker(decoder))

                while True:
                    frame = await capture.read_raw_async()
                    cv2.imshow("local", frame)
                    cv2.waitKey(1)

                await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
