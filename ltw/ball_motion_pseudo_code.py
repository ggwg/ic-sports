from enum import Enum
import cv2
import numpy as np
from math import (sqrt)
import os


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

def draw(x, y, z, radius, color, background):
    if z > 0:
        background = alpha_composite(background, net_image)
        return cv2.circle(background, (int(x), int(y)), int(radius), color, -1)
    else:
        image = cv2.circle(background, (int(x), int(y)), int(radius), color, -1)
        return alpha_composite(image, net_image)

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, 'background_place_holder.jpg')
print(filename)
background = cv2.imread(filename)
background = cv2.resize(background, (500, 500))

# naturally fall down
def loop():
    ball = Ball(100, 100, 10)
    ball.dz = 0.1
    while True:
        # background = np.zeros((500, 500, 3), np.uint8)
        radius = 3 * sqrt(abs(ball.y)) + 2 * ball.z
        image = draw(ball.x, ball.y, ball.z, radius, (255, 255, 255), background)
        print(ball.x, ball.y, ball.z, ball.dx, ball.dy, ball.dz)
        cv2.imshow("background", image)
        cv2.waitKey(20)
        ball.dy += ball.ddy
        ball.y += ball.dy
        ball.x += ball.dx
        ball.z += ball.dz
        if ball.y > 400:
            ball.dy = -ball.dy
            ball.dz = -ball.dz




loop()