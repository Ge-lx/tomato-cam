import time
from datetime import datetime, date, timedelta
import os
import sys
from threading import Thread
from requests import get
from pathlib import Path

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
	thread.start()

# --------------- CONFIG -----------------------------------------------

HOST = 'http://192.168.178.124:8080'
URL_SETTINGS = f'{HOST}/settings'
URL_IMAGE = f'{HOST}/photo.jpg'

IMAGE_ROOT = '/mnt/storage/tomato-cam/'
FFMPEG_COMMAND = lambda cwd: f'ffmpeg -loglevel warning -hide_banner -nostats -pattern_type glob -i "{cwd}/*.jpg" -s 1920x1440 "{cwd}/output.mp4"'

def render_video_for_folder (folder):
	cwd = str(folder)
	print(f'Rendering video for {cwd}...')
	os.system(FFMPEG_COMMAND(cwd))
	print(f'Rendering finished.')

# ---------------------- EVENTS ----------------------------------------

def event__day_finished (folder):
	print('New day started!')
	runAsync(lambda: render_video_for_folder(folder))

lastImageTimestamp = 0
def event__new_image_captured (filename):
	global lastImageTimestamp
	lastImageTimestamp = int(time.time())
	print(f'New image captured: {filename}')

# --------------------  FILE MANAGEMENT  -------------------------------

image_dir = Path(IMAGE_ROOT)
if (image_dir.is_dir() == False):
	sys.exit(f'Cannot find folder "{IMAGE_ROOT}". Please make sure it exists.')

def getFolderForDate (date, create = True):
	foldername = date.isoformat()
	folder = image_dir / foldername

	# Automatically create new folders
	if (folder.is_dir() == False and create):
		folder.mkdir()

		folder_yesterday = getFolderForDate(date.today() - timedelta(days = 1), create = False)
		if (folder_yesterday.is_dir()):
			event__day_finished(folder_yesterday)

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

# Status of last image recording
# Exposure + flash control ?

def route__info (req, params):
	return req.do_JSON({
		'settings': defaultSettings,
		'lastImageTimestamp': lastImageTimestamp
	})

def route__days (req, params):
	days = {}

	for p in Path(IMAGE_ROOT).iterdir():
		if not p.is_dir(): continue
		hasVideo = (p / 'output.mp4').is_file()
		numOfImages = len([q for q in p.iterdir() if q.name.endswith('.jpg')])
		days[p.name] = { 'hasVideo': hasVideo, 'numOfImages': numOfImages }

	return req.do_JSON(days)

def route__static (req, params):
	return req.do_FILE(req.path)

def route__currentImage (req, params):
	refreshImage()
	return req.do_FILE('/current.jpg')

def __routes (router):
	router.addRoute('/favicon.ico', route__static)

	router.addRoute('', route__currentImage)
	router.addRoute('/', route__currentImage)
	router.addRoute('/current.jpg', route__currentImage)

	router.addRoute('/days', route__days)
	router.addRoute('/info', route__info)



# ------------- ROUTER -----------------------

import re, functools, json
from socketserver import TCPServer
from http.server import SimpleHTTPRequestHandler as ReqHandler

class Route:
	def __init__ (self, pathAndParams):
		self.params = []

		def replacePlaceholder (matchobj):
			paramName = matchobj.group(1)
			self.params.append(paramName)
			return '([^/]+)'

		routeRegex = re.sub(':([\w]*)', replacePlaceholder, f'^{pathAndParams}$')
		self.routeRegex = re.compile(routeRegex)

	def exec (self, path):
		match = self.routeRegex.match(path)

		if match is None:
			return False
		else:
			params = {}
			for idx, paramName in enumerate(self.params):
				params[paramName] = match.group(idx + 1)
			return params

class Router:
	def __init__ (self):
		self.routes = []

	def addRoute (self, pathAndParams, handler):
		route = Route(pathAndParams)
		self.routes.append((route, handler))

	def exec (self, req):
		for (route, handler) in self.routes:
			params = route.exec(req.path)
			if params is False:
				continue
			else:
				return handler(req, params)

# Setup the Router

router = Router()
__routes(router)

def route__404 (req, params):
	req.send_error(404)
router.addRoute('.*', route__404)

# Setup the HTTP Server

class RouterRequestHandler(ReqHandler):

	def _set_headers (self):
		self.send_response(200)
		self.send_header('Content-type', 'application/json')
		self.end_headers()
		
	def do_HEAD (self):
		self._set_headers()

	def do_JSON (self, obj): 
		self._set_headers()
		self.wfile.write(json.dumps(obj).encode())

	def do_FILE (self, path):
		self.path = path
		return ReqHandler.do_GET(self)

	def do_GET (self):
		try:
			return router.exec(self)
		except Exception as e:
			self.send_error(500)
			raise e

class TCPReuseServer (TCPServer):
	allow_reuse_address = True

# Start the Server
my_server = TCPReuseServer(("", 9000), RouterRequestHandler)
my_server.serve_forever()
