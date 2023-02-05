from enum import Enum
import cv2
import mediapipe as mp
import numpy as np
import statistics
from math import (sqrt)
import os
import random

SAMPLE_PER_FRAME = 8

class Ball:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.dx = 0
        self.dy = 0
        self.dz = 0
        self.ddy = 0.01

net_image = np.zeros((500, 500, 4), np.uint8)
net_image[250:500, 0:500] = (100, 100, 100, 128)

def alpha_composite(background, foreground):
    alpha = foreground[:, :, 3].astype(float) / 255.0

    image = np.empty(background.shape)

    for ch in range(3):
        image[:, :, ch] = foreground[:, :, ch] * alpha + background[:, :, ch] * (1.0 - alpha)
    image = image.astype(np.uint8)
    return image

def alpha_composite_position(background, foreground, position):
    alpha = foreground[:, :, 3].astype(float) / 255.0
    image = np.copy(background)

    x_from, y_from =  position
    im_x, im_y, *_ = image.shape
    fore_x, fore_y, *_ = foreground.shape
    x_to = min(x_from + fore_x, im_x)
    y_to = min(y_from + fore_y, im_y)
    diff_x, diff_y = (x_to - x_from, y_to - y_from)

    for ch in range(3):
        image[x_from:x_to, y_from:y_to, ch] = (
            foreground[:diff_x, :diff_y, ch] * alpha[:diff_x, :diff_y]
            + background[x_from:x_to, y_from:y_to, ch] 
            * (1.0 - alpha)[:diff_x, :diff_y])
    image = image.astype(np.uint8)
    return image

    

dirname = os.path.dirname(__file__)

ball_image = cv2.imread(os.path.join(dirname, "beach_ball.png"), cv2.IMREAD_UNCHANGED)
head_image = cv2.imread(os.path.join(dirname, "head.png"), cv2.IMREAD_UNCHANGED)

def draw(x, y, z, head, background):
    distance = -z + 50
    radius = 4000 / distance
    
    head_image_transfer = cv2.resize(head_image, (int(radius * 2), int(radius * 2)))
    new_head_image_x = max(head.x - radius, 0)
    new_head_image_y = max(head.y - 2 * radius, 0)
    background = alpha_composite_position(background, head_image_transfer, (int(new_head_image_y), int(new_head_image_x)))

    if z > 0:
        background = alpha_composite(background, net_image)
        ball_image_transfer = cv2.resize(ball_image, (int(radius * 2), int(radius * 2)))
        new_ball_image_x = max(x - radius, 0)
        new_ball_image_y = max(y - 2 * radius, 0)
        background = alpha_composite_position(background, ball_image_transfer, (int(new_ball_image_y), int(new_ball_image_x)))
        
    else:
        ball_image_transfer = cv2.resize(ball_image, (int(radius * 2), int(radius * 2)))
        new_ball_image_x = max(x - radius, 0)
        new_ball_image_y = max(y - 2 * radius, 0)
        background = alpha_composite_position(background, ball_image_transfer, (int(new_ball_image_y), int(new_ball_image_x)))
        background = alpha_composite(background, net_image)

   
    return background

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, 'background_place_holder.jpg')
print(filename)
background = cv2.imread(filename)
background = cv2.resize(background, (500, 500))

# naturally fall down
def loop(pose, mp_pose, cap):
    hand_x_history = [-1, -1, -1, -1, -1]
    hand_y_history = [-1, -1, -1, -1, -1]
    ball = Ball(100, 400, 10)
    hand = Ball(100, 400, 10)
    ball.dz = 0.1

    sample = 0
    while True:
        sample += 1
        if sample == SAMPLE_PER_FRAME // 4:
            hand.x = statistics.fmean([
                hand_x_history[0],
                hand_x_history[1],
                hand_x_history[2],
                hand_x_history[3],
                hand_x_history[4],
            ])
            hand.y = statistics.fmean([
                hand_y_history[0],
                hand_y_history[1],
                hand_y_history[2],
                hand_y_history[3],
                hand_y_history[4],
            ])
        elif sample == SAMPLE_PER_FRAME // 2:
            hand.x = statistics.fmean([
                hand_x_history[0],
                hand_x_history[1],
                hand_x_history[2],
                hand_x_history[3],
                hand_x_history[4],
                hand_x_history[4],
            ])
            hand.y = statistics.fmean([
                hand_y_history[0],
                hand_y_history[1],
                hand_y_history[2],
                hand_y_history[3],
                hand_y_history[4],
                hand_y_history[4],
            ])
        elif sample == 3*(SAMPLE_PER_FRAME // 4):
            hand.x = statistics.fmean([
                hand_x_history[0],
                hand_x_history[1],
                hand_x_history[2],
                hand_x_history[3],
                hand_x_history[4],
                hand_x_history[4],
                hand_x_history[4],
            ])
            hand.y = statistics.fmean([
                hand_y_history[0],
                hand_y_history[1],
                hand_y_history[2],
                hand_y_history[3],
                hand_y_history[4],
                hand_y_history[4],
                hand_y_history[4],
            ])
        if sample == SAMPLE_PER_FRAME:
            hand.x = statistics.fmean([
                hand_x_history[0],
                hand_x_history[1],
                hand_x_history[2],
                hand_x_history[3],
                hand_x_history[4],
                hand_x_history[4],
                hand_x_history[4],
                hand_x_history[4],
            ])
            hand.y = statistics.fmean([
                hand_y_history[0],
                hand_y_history[1],
                hand_y_history[2],
                hand_y_history[3],
                hand_y_history[4],
                hand_y_history[4],
                hand_y_history[4],
                hand_y_history[4],
            ])
            sample = 0
            if cap.isOpened():
                success, image = cap.read()
                if not success:
                    print("Ignoring empty camera frame.")
                else:
                    results = pose.process(image)

                    if results.pose_landmarks:
                        hand_x_history.append(500 - int(results.pose_landmarks.landmark[0].x * 400))
                        hand_y_history.append(320 + int(results.pose_landmarks.landmark[0].y * 400))
                        
                        hand_x_history.pop(0)
                        hand_y_history.pop(0)
                        
                        # Exponentially weighted moving average
                        # hand.x = hand_x_history[0] * 0.161 + hand_x_history[1] * 0.296 + hand_x_history[2] * 0.544
                        # hand.y = hand_y_history[0] * 0.161 + hand_y_history[1] * 0.296 + hand_y_history[2] * 0.544
                        
                        
                        
                        print(hand.x, hand.y)
                        # print('Average left hand pos: ' + str(hands_average[0]), str(hands_average[1]))


        

        # image = draw(hand.x, hand.y, hand.z, background)
        # image = draw(ball.x, ball.y, ball.z, hand, image)
        image = draw(ball.x, ball.y, ball.z, hand, background)
        cv2.imshow("background", image)
        cv2.waitKey(1)

        ball.dy += ball.ddy
        ball.y += ball.dy

        if ball.y < 100:
            pass
        elif ball.y < 200:
            ball.x += ball.dx
        elif ball.y < 300:
            ball.x += 2 * ball.dx

        ball.z += ball.dz

        if ball.y > 400:
            ball.dy = -2
            if ball.x < 100:
                ball.dx = 0.2
            elif ball.x > 350:
                ball.dx = -0.2
            else:
                ball.dx = random.random() * 0.6 - 0.3

            ball.dz = -ball.dz


mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose

cap = cv2.VideoCapture(0)
with mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5) as pose:
    loop(pose, mp_pose, cap)