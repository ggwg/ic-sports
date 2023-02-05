import network
import video

import asyncio
import cv2
import sys
from contextlib import suppress
from typing import Sequence
from dataclasses import dataclass
from ball_motion_pseudo_code import Ball, draw, update_ball_position, hit_back, hitable, hand_meet_ball
import random
import time

import mediapipe as mp
mp_pose = mp.solutions.pose

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

async def local_postion_worker(queue: asyncio.Queue, hand):
    i = 0
    hand_x_history = [-1, -1, -1]
    hand_y_history = [-1, -1, -1]
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while True:
            frame = await queue.get()
            frame = cv2.resize(frame, (160, 120))
            if i % 3 == 0:
                results = pose.process(frame)

                if results.pose_landmarks:
                    hand_x_history.append(500 - int(results.pose_landmarks.landmark[0].x * 400))
                    hand_y_history.append(320 + int(results.pose_landmarks.landmark[0].y * 400))
                    
                    hand_x_history.pop(0)
                    hand_y_history.pop(0)
                    
                    # Exponentially weighted moving average
                    hand.x = hand_x_history[0] * 0.161 + hand_x_history[1] * 0.296 + hand_x_history[2] * 0.544
                    hand.y = hand_y_history[0] * 0.161 + hand_y_history[1] * 0.296 + hand_y_history[2] * 0.544
                    
                    print(hand.x, hand.y)
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

async def server_ctrl_loop(remote: network.Remote, ball):
    while True:
        try:
            ball.x, ball.y, ball.z = (await remote.recv_control()).values()
        except Exception as e:
            print("Error in server ctrl loop:", e)

async def client_ctrl_loop(remote: network.Remote, ball):
    while True:
        try:
            ball.x, ball.y, ball.z = (await remote.recv_control()).values()
        except Exception as e:
            print("Error in client ctrl loop:", e)



@dataclass
class Hand:
    x: int
    y: int


async def main():
    if sys.argv[1] == "client":
        remote = network.Client(sys.argv[2])
        clientOrServer = "client"
    else:
        remote = network.Server()
        clientOrServer = "server"
    
    encoder = video.VideoEnc(is_server=(clientOrServer == "server"))

    if clientOrServer == "client":
        encoder.run()

    frame_queue = asyncio.Queue(1)
    frame_queue_2 = asyncio.Queue(1)
    hand = Hand(0, 0)
    ball = Ball(random.randint(100, 500), 400, 24)

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
                asyncio.create_task(h264_encode_worker(frame_queue, encoder))
                asyncio.create_task(frame_queue_tee(capture, (frame_queue, frame_queue_2)))
                asyncio.create_task(local_postion_worker(frame_queue_2, hand))
                if clientOrServer == "server":
                    asyncio.create_task(server_ctrl_loop(remote, ball))
                else:
                    asyncio.create_task(client_ctrl_loop(remote, ball))
                # asynio.create_task(remote_render_worker(decoder))

                while True:
                    print("$$$$$$$$$$$$$", time.time())
                    try:
                        if clientOrServer == "server":
                            update_ball_position(ball)
                            asyncio.create_task(remote.send_control({"x": ball.x, "y": ball.y, "z": -ball.z}))
                        frame = await decoder.read_raw_async()
                        # if hitable(ball) and hand_meet_ball(ball, hand):
                        if ball.y > 400:
                            if clientOrServer == "server":
                                hit_back(ball)
                            else:
                                hit_back(ball)
                                asyncio.create_task(remote.send_control({"x": ball.x, "y": ball.y, "z": -ball.z}))
                        frame = draw(ball.x, ball.y, ball.z, frame)
                        print("ball pos: ", ball.x, ball.y, ball.z)
                        cv2.circle(frame, (int(hand.x), int(hand.y)), 10, (0, 0, 255), -1)
                        cv2.imshow("main", frame)
                        cv2.waitKey(100)
                    except Exception as e:
                        print("Error in remote render worker:", e)
                    # frame = await frame_queue_2.get()

                    # cv2.imshow("local", frame)
                    cv2.waitKey(1)

                await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
