import network
import video
import traceback

import asyncio
import cv2
import sys
from contextlib import suppress, contextmanager
from typing import Sequence
from dataclasses import dataclass
from ball_motion import Ball, draw, hand_meets_ball
import random
import time
import pickle

import mediapipe as mp
mp_pose = mp.solutions.pose


@contextmanager
def dummy_resource():
    try:
        yield None
    finally:
        pass


@dataclass
class Hand:
    x: int
    y: int


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
            # print("got h264 frame")
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


async def local_position_worker(queue: asyncio.Queue, hand):
    i = 0
    hand_x_history = [-1, -1, -1]
    hand_y_history = [-1, -1, -1]
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while True:
            frame = await queue.get()
            frame = cv2.resize(frame, (160, 120))
            if i % 2 == 0:
                results = pose.process(frame)

                if results.pose_landmarks:
                    hand_x_history.append(
                        640 - int(results.pose_landmarks.landmark[0].x * 400))
                    hand_y_history.append(
                        30 + int(results.pose_landmarks.landmark[0].y * 400))

                    hand_x_history.pop(0)
                    hand_y_history.pop(0)

                    # Exponentially weighted moving average
                    hand.x = hand_x_history[0] * 0.161 + \
                        hand_x_history[1] * 0.296 + hand_x_history[2] * 0.544
                    hand.y = hand_y_history[0] * 0.161 + \
                        hand_y_history[1] * 0.296 + hand_y_history[2] * 0.544

                    print(f"Hand position: {hand.x:.2f}, {hand.y:.2f}")
                    # print('Average left hand pos: ' + str(hands_average[0]), str(hands_average[1]))
            i += 1


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


async def server_ctrl_loop(remote: network.Remote, ball: Ball):
    while True:
        try:
            ball.x, ball.y, ball.z = await remote.recv_control()
            ball.hit_back()
        except Exception as e:
            print("Error in server ctrl loop:", e)


async def client_ctrl_loop(remote: network.Remote, ball: Ball):
    while True:
        try:
            ball.x, ball.y, ball.z = await remote.recv_control()
        except Exception as e:
            print("Error in client ctrl loop:", e)


async def server_logic_loop(ball: Ball, remote: network.Remote, hand):
    while True:
        try:
            await asyncio.sleep(0.02)
            if remote.connected:
                ball.update_pos()
                asyncio.create_task(remote.send_control([ball.x, ball.y, -ball.z]))
                if ball.hitable and hand_meets_ball(ball, hand):
                    ball.hit_back()
        except Exception as e:
            traceback.print_exc()
            print("Error in server logic loop:", e)


async def client_logic_loop(ball: Ball, remote: network.Remote, hand):
    while True:
        try:
            ball.x, ball.y, ball.z = await remote.recv_control()
            if ball.hitable and hand_meets_ball(ball, hand):
                asyncio.create_task(remote.send_control(
                    [ball.x, ball.y, -ball.z]))
        except Exception as e:
            print("Error in client logic loop:", e)


async def remote_render_worker(ball: Ball, hand: Hand, decoder: video.VideoDec):
    while True:
        try:
            frame = await decoder.read_raw_async()
            frame = cv2.flip(frame, 1)
            frame = draw(ball, frame)
            print("ball pos:", ball)
            cv2.circle(frame, (int(hand.x), int(hand.y)),
                       10, (0, 0, 255), -1)
            cv2.imshow("main", frame)
            cv2.waitKey(1)
        except Exception as e:
            print("Error in remote render worker:", e)


async def main():
    if sys.argv[1] == "client":
        remote = network.Client(sys.argv[2])
        client_or_server = "client"
    else:
        remote = network.Server()
        client_or_server = "server"

    encoder = video.VideoEnc(is_server=(client_or_server == "server"))

    frame_queue = asyncio.Queue(1)
    frame_queue_2 = asyncio.Queue(1)
    hand = Hand(0, 0)
    ball = Ball(random.randint(100, 500), 300, 0)

    with video.VideoDec() as decoder, video.VideoCap() as capture, encoder if client_or_server == "client" else dummy_resource():
        def conn_on_cb(_):
            print("Connection on")
            ball = Ball(random.randint(100, 500), 300, 0)

            encoder.run()

        def conn_off_cb(_):
            print("Connection off")
            encoder.stop()
            print("Encoder stopped")

        remote.conn_on_cb = conn_on_cb
        remote.conn_off_cb = conn_off_cb

        async with remote:
            print("starting")
            asyncio.create_task(h264_decode_worker(remote, decoder))
            asyncio.create_task(video_transmitter_worker(remote, encoder))
            asyncio.create_task(h264_encode_worker(frame_queue, encoder))
            asyncio.create_task(frame_queue_tee(
                capture, (frame_queue, frame_queue_2)))
            asyncio.create_task(local_position_worker(frame_queue_2, hand))
            if client_or_server == "server":
                asyncio.create_task(server_ctrl_loop(remote, ball))
                asyncio.create_task(server_logic_loop(ball, remote, hand))
            else:
                asyncio.create_task(client_ctrl_loop(remote, ball))
                asyncio.create_task(client_logic_loop(ball, remote, hand))

            asyncio.create_task(remote_render_worker(ball, hand, decoder))

            await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
