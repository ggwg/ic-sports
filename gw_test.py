from PySide6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout, QPushButton
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QBrush
from PySide6.QtCore import Signal, Slot, Qt, QThread, QObject, QTimer
from pynput.mouse import Button, Controller
from pynput.keyboard import Key
from pynput.keyboard import Controller as KeyboardController
from screeninfo import get_monitors
from datetime import datetime
from sys import platform
from numpy import average
import sys
import cv2
import math
import numpy as np
import mediapipe as mp
import enum

keyboard = KeyboardController()

# Mediapipe Setup
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

# Screen size calculation
monitor = get_monitors()[0]
SCREEN_WIDTH = monitor.width
SCREEN_HEIGHT = monitor.height

DEVICE_INDEX = -1 if platform == "linux" else 0

mouse = Controller()

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
        background = np.zeros((500, 500, 3), np.uint8)
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
            
class Action(enum.Enum):
    resting = 1
    leftclick = 2
    scroll = 3

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Testing")
        size_ratio = 0.6
        self.disply_width = 640 * size_ratio
        self.display_height = 480 * size_ratio
        
        # Placeholder
        self.game_placeholder = self.convert_cv_qt(cv2.imread('cat1.jpeg'))

        # Create the gameplay screen
        self.game_label = QLabel(self)
        self.game_label.setPixmap(self.game_placeholder)
        self.game_label.resize(self.disply_width, self.display_height)


        # Create a vertical box layout and add the two labels
        vbox = QVBoxLayout()
        vbox.addWidget(self.game_label)
        
        # Set the vbox layout as the widgets layout
        self.setLayout(vbox)

    
    def closeEvent(self, event):
        self.thread.stop()
        event.accept()

    
    
    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.disply_width, self.display_height, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)

if __name__=="__main__":
    app = QApplication(sys.argv)
    a = App()
    a.show()
    sys.exit(app.exec())