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

net_image = np.zeros((500, 500, 3), np.uint8)
net_image[250:500, 0:500] = (100, 100, 100)

def draw(x, y, z, radius, color, background):
    if z > 0:
        background += net_image
        return cv2.circle(background, (int(x), int(y)), int(radius), color, -1)
    else:
        image = cv2.circle(background, (int(x), int(y)), int(radius), color, -1)
        # overlay net image onto background
        image = cv2.addWeighted(image,0.7,net_image,1.0,0)
        return image

# naturally fall down
def loop():
    ball = Ball(100, 100, 10)
    ball.dz = 0.1
    while True:
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, 'background_place_holder.jpg')
        print(filename)
        background = cv2.imread(filename)
        background = cv2.resize(background, (500, 500))
        # background = np.zeros((500, 500, 3), np.uint8)
        radius = 3 * sqrt(abs(ball.y)) + 2 * ball.z
        image = draw(ball.x, ball.y, ball.z, radius, (255, 255, 255), background)
        print(ball.x, ball.y, ball.z, ball.dx, ball.dy, ball.dz)
        cv2.imshow("background", image)
        cv2.waitKey(10)
        ball.dy += ball.ddy
        ball.y += ball.dy
        ball.x += ball.dx
        ball.z += ball.dz
        if ball.y > 400:
            ball.dy = -ball.dy
            ball.dz = -ball.dz




loop()