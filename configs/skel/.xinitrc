#!/bin/sh
# ScribeBox X session startup

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Set keyboard repeat rate
xset r rate 250 30

# Start ScribeBox
exec python3 -m scribebox --models-dir /opt/scribebox/models --data-dir /data/scribebox
