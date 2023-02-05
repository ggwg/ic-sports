from enum import Enum
import cv2
import numpy as np
from math import (sqrt)
import os
import random


class Side(Enum):
    A = 0
    B = 1

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
print(ball_image.shape)
print(ball_image)

def draw(x, y, z, background):
    distance = -z + 50
    radius = 4000 / distance
    if z > 0:
        background = alpha_composite(background, net_image)
        ball_image_transfer = cv2.resize(ball_image, (int(radius * 2), int(radius * 2)))
        new_ball_image_x = max(x - radius, 0)
        new_ball_image_y = max(y - 2 * radius, 0)
        background = alpha_composite_position(background, ball_image_transfer, (int(new_ball_image_y), int(new_ball_image_x)))
        return background
    else:
        ball_image_transfer = cv2.resize(ball_image, (int(radius * 2), int(radius * 2)))
        new_ball_image_x = max(x - radius, 0)
        new_ball_image_y = max(y - 2 * radius, 0)
        background = alpha_composite_position(background, ball_image_transfer, (int(new_ball_image_y), int(new_ball_image_x)))
        return alpha_composite(background, net_image)

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, 'background_place_holder.jpg')
print(filename)
background = cv2.imread(filename)
background = cv2.resize(background, (500, 500))

# naturally fall down
def loop():
    ball = Ball(100, 400, 10)
    ball.dz = 0.1
    while True:
        # background = np.zeros((500, 500, 3), np.uint8)
        image = draw(ball.x, ball.y, ball.z, background)
        # print(ball.x, ball.y, ball.z, ball.dx, ball.dy, ball.dz)
        print(ball.x, ball.y, ball.z)
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


loop()