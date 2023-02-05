import sys
import game_ui
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QWidget)
from PyQt5.QtGui import (QFont, QPixmap)
from PyQt5.QtCore import Qt

class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('I See Sports - Gameplay')

        # Create title
        title = QLabel('I See Sports', self)
        title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(24)
        title.setFont(font)

        # Create image
        # loading image
        image = QLabel(self)
        pixmap = QPixmap('assets/beach_ball.png').scaledToWidth(200)
        # adding image to label
        image.setPixmap(pixmap)
        image.resize(100, 100)

        # Create description
        description = QLabel('How to play: Opponents compete against each other to play volleyball with their head. Stay a distance of around 0.5m away from the screen, and move your head under the ball to hit the ball back to your opponent. Your opponent will gain a point if you let the ball drop!', self)
        description.setAlignment(Qt.AlignCenter)
        # description.setWordWrap(True)
        description.setMaximumWidth(500)

        # Create start button
        start_button = QPushButton('Start', self)
        start_button.clicked.connect(self.start_clicked)
        start_button.setFixedSize(100, 50)
        start_button.setStyleSheet("background-color: green; color: white; font-size: 20px;")

        # Set button layout
        layout = QVBoxLayout()
        layout.addSpacing(50)
        layout.addWidget(title, alignment=Qt.AlignCenter)
        layout.addSpacing(50)
        layout.addWidget(image, alignment=Qt.AlignCenter)
        layout.addSpacing(50)
        layout.addWidget(description, alignment=Qt.AlignCenter)
        layout.addSpacing(50)
        button_layout = QHBoxLayout()
        button_layout.addSpacing(450)
        button_layout.addWidget(start_button)
        layout.addLayout(button_layout)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def start_clicked(self):
        # Link to another page when start button is clicked
        self.next_page = game_ui.App()
        self.next_page.show()
        
# class AnotherPage(QMainWindow):
#     def __init__(self):
#         super().__init__()

#         self.initUI()
        
#     def initUI(self):
#         self.setWindowTitle('Another Page')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    menu = MainMenu()
    menu.show()
    sys.exit(app.exec_())


