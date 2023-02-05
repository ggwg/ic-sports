### Setup


```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running

Development of main app (including user interface) is in main.py. It calls the UI code for the game in game.py as a new window.

```
python3 main.py
```

Tony's code is in /ltw directory. Peter's code is in /peter directory.

```
python3 ltw/ball_motion_pseudo_code.py
```

Old code is in /old_cv_project directory.


# ic-sports

dependencies

```bash
brew install gstreamer gst-plugins-bad gst-plugins-good gst-plugins-ugly gst-plugins-base gst-libav pygobject3
```

```brew
brew install pygobject3
```

# Misc

Setting up PyQt5 (Graphical User Interface):

```bash
pip install pyqt5 --config-settings --confirm-license= --verbose
```