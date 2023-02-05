#!/bin/sh

export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/opt/homebrew/lib/gstreamer-1.0
exec python3 game_ui.py "$@"
