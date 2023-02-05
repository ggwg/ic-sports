from PyQt5 import QtGui
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap
import sys
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread
import numpy as np
from enum import Enum
import cv2
import mediapipe as mp
import statistics
from math import (sqrt)
import os
import random
import network
import video
import traceback
import asyncio
import sys
from contextlib import suppress, contextmanager
from typing import Sequence
from dataclasses import dataclass
from ball_motion import Ball, draw, hand_meets_ball, alpha_composite_position, guy_image
import random
import time
import pickle

import mediapipe as mp
mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands


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
    hit: bool

@dataclass
class Score:
    my: int = 0
    competitor: int = 0


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


async def local_position_worker(queue: asyncio.Queue, player: Hand, ball: Ball, remote: network.Remote, is_hand=False):
    i = 0
    x_history = [-1, -1, -1]
    y_history = [-1, -1, -1]
    if is_hand:
        with mp_hands.Hands(model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
            while True:
                frame = await queue.get() 
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                print("frame get")
                # frame = cv2.resize(frame, (320, 240))
                if i % 2 == 0:
                    results = hands.process(frame)

                    if results.multi_hand_landmarks:
                        hand_landmarks = results.multi_hand_landmarks[-1]
                        x_history.append(
                                640 - int(hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].x * 700))
                        y_history.append(
                            50 + int(hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y * 400))
                            
                        x_history.pop(0)
                        y_history.pop(0)

                        # Exponentially weighted moving average
                        player.x = x_history[0] * 0.161 + \
                            x_history[1] * 0.296 + x_history[2] * 0.544
                        player.y = y_history[0] * 0.161 + \
                            y_history[1] * 0.296 + y_history[2] * 0.544
                        print(f"HAND position: {player.x:.2f}, {player.y:.2f}")
                        if ball.hitable and hand_meets_ball(ball, player):
                            print("Hand hits ball")
                            player.hit = True
                            asyncio.create_task(remote.send_control(
                                [ball.x, ball.y, -ball.z, -ball.dz]))
                            ball.hit_back()
                        else:
                            player.hit = False
    else:
        with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
            while True:
                frame = await queue.get()
                frame = cv2.resize(frame, (160, 120))
                if i % 2 == 0:
                    results = pose.process(frame)

                    if results.pose_landmarks:
                        x_history.append(
                            640 - int(results.pose_landmarks.landmark[0].x * 700))
                        y_history.append(
                            50 + int(results.pose_landmarks.landmark[0].y * 400))

                        x_history.pop(0)
                        y_history.pop(0)

                        # Exponentially weighted moving average
                        player.x = x_history[0] * 0.161 + \
                            x_history[1] * 0.296 + x_history[2] * 0.544
                        player.y = y_history[0] * 0.161 + \
                            y_history[1] * 0.296 + y_history[2] * 0.544

                        print(f"HEAD position: {player.x:.2f}, {player.y:.2f}")
                        if ball.hitable and hand_meets_ball(ball, player):
                            print("Head hits ball")
                            player.hit = True
                            asyncio.create_task(remote.send_control(
                                [ball.x, ball.y, -ball.z, -ball.dz]))
                            ball.hit_back()
                        else:
                            player.hit = False
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
            ball.x, ball.y, ball.z, ball.dz = await remote.recv_control()
            ball.hit_back()
        except Exception as e:
            print("Error in server ctrl loop:", e)


async def client_ctrl_loop(remote: network.Remote, ball: Ball, score: Score):
    while True:
        try:
            ball.x, ball.y, ball.z, ball.dz, score.competitor, score.my = await remote.recv_control()
        except Exception as e:
            print("Error in client ctrl loop:", e)


async def server_logic_loop(ball: Ball, remote: network.Remote, hand: Hand, score: Score):
    while True:
        try:
            await asyncio.sleep(0.02)
            if remote.connected:
                auto_hit_back = ball.update_pos()
                if auto_hit_back:
                    if ball.z > 0:
                        score.competitor += 1
                    else:
                        score.my += 1
                asyncio.create_task(remote.send_control(
                    [ball.x, ball.y, -ball.z, -ball.dz, score.my, score.competitor]))
        except Exception as e:
            traceback.print_exc()
            print("Error in server logic loop:", e)


async def remote_render_worker(ball: Ball, hand: Hand, decoder: video.VideoDec, score: Score, change_pixmap_signal):
    while True:
        try:
            frame = await decoder.read_raw_async()
            frame = cv2.flip(frame, 1)
            frame = draw(ball, frame)
            print("ball pos:", ball)

            color = (0, 0, 255) if not hand.hit else (255, 0, 0)
            frame = alpha_composite_position(frame, guy_image, (int(hand.y), int(hand.x)))
            
            cv2.putText(frame, f"{score.my}:{score.competitor}", (video.IMAGE_WIDTH // 2, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            # cv2.imshow("main", frame)
            # cv2.waitKey(1)
            change_pixmap_signal.emit(frame)
        except Exception as e:
            traceback.print_exc()
            print("Error in remote render worker:", e)


async def main(change_pixmap_signal):
    if sys.argv[1] == "client":
        remote = network.Client(sys.argv[2])
        client_or_server = "client"
    else:
        remote = network.Server()
        client_or_server = "server"

    encoder = video.VideoEnc(is_server=(client_or_server == "server"))

    frame_queue = asyncio.Queue(1)
    frame_queue_2 = asyncio.Queue(1)
    hand = Hand(0, 0, False)
    ball = Ball(random.randint(100, 500), 300, 0)
    score = Score()

    with video.VideoDec() as decoder, video.VideoCap() as capture, encoder if client_or_server == "client" else dummy_resource():
        def conn_on_cb(_):
            nonlocal ball
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
            asyncio.create_task(local_position_worker(
                frame_queue_2, hand, ball, remote, is_hand=False))
            if client_or_server == "server":
                asyncio.create_task(server_ctrl_loop(remote, ball))
                asyncio.create_task(server_logic_loop(ball, remote, hand, score))
            else:
                asyncio.create_task(client_ctrl_loop(remote, ball, score))

            asyncio.create_task(remote_render_worker(ball, hand, decoder, score, change_pixmap_signal))

            await asyncio.Future()


# if __name__ == "__main__":
#     asyncio.run(main())

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._run_flag = True

    def run(self):
        asyncio.run(main(self.change_pixmap_signal))
        # self.change_pixmap_signal.emit(image)

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False
        self.wait()


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt live label demo")
        self.disply_width = 640
        self.display_height = 480
        # create the label that holds the image
        self.image_label = QLabel(self)
        self.image_label.resize(self.disply_width, self.display_height)
        # create a text label
        self.textLabel = QLabel('Webcam')

        # create a vertical box layout and add the two labels
        vbox = QVBoxLayout()
        vbox.addWidget(self.image_label)
        vbox.addWidget(self.textLabel)
        # set the vbox layout as the widgets layout
        self.setLayout(vbox)

        # create the video capture thread
        self.thread = VideoThread()
        # connect its signal to the update_image slot
        self.thread.change_pixmap_signal.connect(self.update_image)
        # start the thread
        self.thread.start()

    def closeEvent(self, event):
        self.thread.stop()
        event.accept()



    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        print("******")
        """Updates the image_label with a new opencv image"""
        qt_img = self.convert_cv_qt(cv_img)
        self.image_label.setPixmap(qt_img)
    
    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.disply_width, self.display_height, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)
    
if __name__=="__main__":
    app = QApplication(sys.argv)
    a = App()
    a.show()
    sys.exit(app.exec_())