from enum import Enum
import cv2
import numpy as np
from math import (sqrt)
import os
import random
from video import IMAGE_HEIGHT, IMAGE_WIDTH


class Ball:
    def __init__(self, x, y, z, frame_height=IMAGE_HEIGHT, frame_width=IMAGE_WIDTH):
        self.x = x
        self.y = y
        self.z = z
        self.dx = 0
        self.dy = 0
        self.dz = 0.5
        self.ddy = 0.12
        self.frame_height = frame_height
        self.frame_width = frame_width

    @property
    def display_radius(self):
        return np.arctan2(50, -self.z + 30) * 50

    def update_pos(self):
        auto_hit_back = False
        self.dy += self.ddy
        self.y += self.dy

        if self.x < 80:
            self.x += 0.5 * self.dx
        elif self.x > self.frame_width - 80:
            self.x += 0.5 * self.dx
        else:
            if self.y < 100:
                pass
            elif self.y < 200:
                self.x += self.dx
            elif self.y < 300:
                self.x += 2 * self.dx
            elif self.y > self.frame_height - 10 or self.x < -5 or self.x > self.frame_width + 5 or self.z > 30:
                auto_hit_back = True
                self.hit_back()

        self.z += self.dz
        return auto_hit_back


    @property
    def hitable(self):
        return self.y > 300 and self.z > 15 and self.dz > 0

    def hit_back(self):
        self.dy = -7
        self.y = 400
        self.dz = -self.dz
        self.z = 24 if self.z > 0 else -24

        if self.x < 80:
            self.dx = 0.2
        elif self.x > self.frame_width - 80:
            self.dx = -0.2
        else:
            self.dx = random.random() * 1.5 - 0.75

    def __repr__(self) -> str:
        return f"{self.x:.2f}, {self.y:.2f}, {self.z:.2f}"
    
    @property
    def xyz(self) -> tuple:
        return (self.x, self.y, self.z)


net_image = np.zeros((IMAGE_HEIGHT, IMAGE_WIDTH, 4), np.uint8)
net_image[IMAGE_HEIGHT // 2:IMAGE_HEIGHT, 0:IMAGE_WIDTH] = (100, 100, 100, 128)


def alpha_composite(background, foreground):
    alpha = foreground[:, :, 3].astype(float) / 255.0
    image = np.empty(background.shape)
    for ch in range(3):
        image[:, :, ch] = foreground[:, :, ch] * \
            alpha + background[:, :, ch] * (1.0 - alpha)
    image = image.astype(np.uint8)
    return image


def alpha_composite_position(background, foreground, position):
    alpha = foreground[:, :, 3].astype(float) / 255.0
    image = np.copy(background)

    x_from, y_from = position
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

# ball_image = cv2.imread(os.path.join(
#     dirname, "beach_ball.png"), cv2.IMREAD_UNCHANGED)
# print(ball_image.shape)
# print(ball_image)
ball_images = [
    cv2.imread(os.path.join(dirname, "assets/1.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/2.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/3.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/4.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/5.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/6.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/7.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/8.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/9.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/10.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/11.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/12.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/13.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/14.png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(dirname, "assets/15.png"), cv2.IMREAD_UNCHANGED),
]

guy_image = cv2.imread(os.path.join(dirname, "assets/asian.png"), cv2.IMREAD_UNCHANGED)
guy_image = cv2.resize(guy_image, (30, 30))

iteration = 0
def draw(ball: Ball, background):
    global iteration
    global ball_images
    iteration += 1
    x, y, z = ball.x, ball.y, ball.z
    radius = ball.display_radius
    ball_image = ball_images[(iteration // 3) % 15]
    # print(radius)
    if z > 0:
        background = alpha_composite(background, net_image)
        ball_image_transfer = cv2.resize(
            ball_image, (int(radius * 2), int(radius * 2)))
        new_ball_image_x = max(x - radius, 0)
        # new_ball_image_y = max(y - 2 * radius, 0)
        new_ball_image_y = max(y - radius, 0)
        background = alpha_composite_position(
            background, ball_image_transfer, (int(new_ball_image_y), int(new_ball_image_x)))
        if ball.hitable:
            color = (255, 0, 0)
        else:
            color = (255, 255, 255)
        background = cv2.circle(background, (int(x), int(y)), 10, color, 0)
        return background
    else:
        ball_image_transfer = cv2.resize(
            ball_image, (int(radius * 2), int(radius * 2)))
        new_ball_image_x = max(x - radius, 0)
        # new_ball_image_y = max(y - 2 * radius, 0)
        new_ball_image_y = max(y - radius, 0)
        background = alpha_composite_position(
            background, ball_image_transfer, (int(new_ball_image_y), int(new_ball_image_x)))
        background = alpha_composite(background, net_image)
        if ball.hitable:
            color = (255, 0, 0)
        else:
            color = (255, 255, 255)
        background = cv2.circle(background, (int(x), int(y)), 10, color, 0)
        return background


def hand_meets_ball(ball: Ball, hand):
    return sqrt((hand.x - ball.x) ** 2 + (ball.y - hand.y) ** 2) <= ball.display_radius * 1.5


if __name__ == "__main__":
    bg_image = cv2.imread("background_place_holder.jpg", cv2.IMREAD_UNCHANGED)
    bg_image = cv2.resize(bg_image, (IMAGE_WIDTH, IMAGE_HEIGHT))
    ball = Ball(random.randint(100, 500), 300, 0)
    while True:
        ball.update_pos()
        print("ball pos:", ball)
        if ball.y > 480:
            ball.hit_back()

        frame = draw(ball, bg_image)
        cv2.imshow("main", frame)
        cv2.waitKey(10)
