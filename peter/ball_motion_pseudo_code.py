from enum import Enum
import cv2
import numpy as np
from math import (sqrt)
import os
import random

class Ball:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.dx = 0
        self.dy = 0
        self.dz = 0.5
        self.ddy = 0.12

net_image = np.zeros((480, 640, 4), np.uint8)
net_image[300:480, 0:640] = (100, 100, 100, 128)

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
print(ball_image.shape)
print(ball_image)

def find_radius(z):
    return 4000 / (-z + 50)

def draw(x, y, z, background):
    radius = find_radius(z)
    if z > 0:
        background = alpha_composite(background, net_image)
        ball_image_transfer = cv2.resize(ball_image, (int(radius * 2), int(radius * 2)))
        new_ball_image_x = max(x - radius, 0)
        new_ball_image_y = max(y - 2 * radius, 0)
        background = alpha_composite_position(background, ball_image_transfer, (int(new_ball_image_y), int(new_ball_image_x)))
        background = cv2.circle(background, (int(x), int(y)), 10, (255, 255, 255), 1)
        return background
    else:
        ball_image_transfer = cv2.resize(ball_image, (int(radius * 2), int(radius * 2)))
        new_ball_image_x = max(x - radius, 0)
        new_ball_image_y = max(y - 2 * radius, 0)
        background = alpha_composite_position(background, ball_image_transfer, (int(new_ball_image_y), int(new_ball_image_x)))
        background = alpha_composite(background, net_image)
        background = cv2.circle(background, (int(x), int(y)), 10, (255, 255, 255), 1)
        return background



def hit_back(ball):
    ball.dy = -6
    ball.y = 400
    ball.dz = -0.5 if ball.dz > 0 else 0.5
    ball.z = 24 if ball.z > 0 else -24

    if ball.x < 100:
        ball.dx = 0.2
    elif ball.x > 500:
        ball.dx = -0.2
    else:
        ball.dx = random.random() * 1.5 - 0.75

def update_ball_position(ball):
    ball.dy += ball.ddy
    ball.y +=  ball.dy

    if ball.x < 100:
        ball.x += 0.5 * ball.dx
    elif ball.x > 500:
        ball.x += 0.5 * ball.dx
    else:
        if ball.y < 100:
            pass
        elif ball.y < 200:
            ball.x += ball.dx
        elif ball.y < 300:
            ball.x += 2 * ball.dx

    ball.z += ball.dz



def hitable(ball):
    return ball.y > 350 and ball.z > 20 and ball.dz > 0

def hand_meet_ball(ball, hand):
    radius = find_radius(ball.z)
    return sqrt((hand.x - ball.x) ** 2 + (ball.y + radius - hand.y) ** 2) < 200

