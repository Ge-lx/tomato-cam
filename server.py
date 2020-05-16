import time
from datetime import datetime, date, timedelta
import os
import sys
from threading import Thread
from requests import get
from pathlib import Path

import http.server
import socketserver
from http.server import SimpleHTTPRequestHandler as ReqHandler

# ---------------------- UTILS -----------------------------------------

def setInterval (callback, interval):
    cancelled = False

    def timerExecutor ():
        nonlocal cancelled

        nextCallTimestamp = time.time()
        while cancelled != True:
            nextCallTimestamp = nextCallTimestamp + interval
            try:
            	callback()
            except Exception as e:
            	print(f'Exception while executing interval callback: {e}')
            time.sleep(max(0, nextCallTimestamp - time.time()))

    def cancelTimer ():
        nonlocal cancelled
        cancelled = True

    timerThread = Thread(target=timerExecutor, daemon=True)
    timerThread.start()
    return cancelTimer

def runAsync (callback):
	thread = Thread(target=callback, daemon=True)
	timerThread.start()

# --------------- CONFIG -----------------------------------------------

HOST = 'http://192.168.178.124:8080'
URL_SETTINGS = f'{HOST}/settings'
URL_IMAGE = f'{HOST}/photo.jpg'

IMAGE_ROOT = '/mnt/storage/tomato-cam/'
FFMPEG_COMMAND = lambda image_glob: f'ffmpeg -pattern_type glob -i {image_glob} -s 1920x1440 output.mp4'

def render_video_for_folder (folder):
	image_glob = f'"{str(folder_yesterday)}/*.jpg"'
	print(f'Rendering video for {image_glob}...')
	os.system(FFMPEG_COMMAND(image_glob))
	print(f'Rendering finished.')

# ---------------------- EVENTS ----------------------------------------

def event__new_day_started ():
	print('New day started!')
	folder_yesterday = getFolderForDate(date.today() - timedelta(days = 1), create = False)
	runAsync(lambda: render_video_for_folder(folder_yesterday))

def event__new_image_captured (filename):
	print(f'New image captured: {filename}')

# --------------------  FILE MANAGEMENT  -------------------------------

image_dir = Path(IMAGE_ROOT)
if (image_dir.is_dir() == False):
	sys.exit(f'Cannot find folder "{IMAGE_ROOT}". Please make sure it exists.')

def getFolderForDate (date, create = True):
	foldername = date.isoformat()
	folder = image_dir / foldername

	# Automatically create new folders
	if (folder.is_dir() == False & create):
		folder.mkdir()
		event__new_day_started()

	return folder

def getPathForImage ():
	folder = getFolderForDate(date.today())
	filename = f'{str(int(time.time()))}.jpg'
	return str(folder / filename)

# -------------------- IMAGE ACQUISITION -------------------------------

defaultSettings = {
	'flashmode': 'auto',
	'focusmode': 'infinity',
    'whitebalance': 'cloudy-daylight'
}
def getCurrentExposure ():
    hour_now = datetime.now().hour
    return 4 if (hour_now < 6 or hour_now > 20) else 0

def setCurrentSettings ():
	defaultSettings['exposure'] = getCurrentExposure()
	print(f'Current settings: {defaultSettings}')

	for setting in defaultSettings:
		value = defaultSettings[setting]
		get(f'{URL_SETTINGS}/{setting}?set={value}')

# ---------------------------------------

def refreshImage ():
	setCurrentSettings()
	image_path = Path('./current.jpg')
	if (image_path.exists()):
		image_path.unlink

	r = get(URL_IMAGE, stream = True)
	
	# Make sure to always close the file
	with open(str(image_path), 'wb') as fd:
		for chunk in r.iter_content(chunk_size = 128):
			fd.write(chunk)

def refreshAndSaveImage ():
    refreshImage()
    filename = getPathForImage()
    os.system(f'cp current.jpg {filename}')
    event__new_image_captured(filename)
    
setInterval(refreshAndSaveImage, 3 * 60) # 20 images per hour | ~28GB per month at 2MB per image
# ------------------ HTTP ----------------------------------------------

class CustomRequestHandler(ReqHandler):
    def do_GET(self):
        if self.path in ['/current', '', '/']:
            refreshImage()
            self.path = 'current.jpg'
            return ReqHandler.do_GET(self)
        else:
            return ReqHandler.send_error(self, 404)
        
# start the server
my_server = socketserver.TCPServer(("", 80), CustomRequestHandler)
my_server.serve_forever()
