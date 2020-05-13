import time
import wget
from datetime import datetime as date
import os
from threading import Thread
from requests import get

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
            except:
            	print('Exception while executing interval callback')
            time.sleep(max(0, nextCallTimestamp - time.time()))

    def cancelTimer ():
        nonlocal cancelled
        cancelled = True

    timerThread = Thread(target=timerExecutor, daemon=True)
    timerThread.start()
    return cancelTimer

# -------------------- IMAGE ACQUISITION -------------------------------

defaultSettings = {
	'flashmode': 'auto',
	'focusmode': 'infinity',
    'whitebalance': 'cloudy-daylight'
}
def getCurrentExposure ():
    hour_now = date.now().hour
    return 4 if (hour_now < 6 or hour_now > 20) else 0

def setCurrentSettings ():
	defaultSettings['exposure'] = getCurrentExposure()
	print(f'Current settings: {defaultSettings}')

	for setting in defaultSettings:
		value = defaultSettings[setting]
		get(f'http://192.168.178.124:8080/settings/{setting}?set={value}')

# ---------------------------------------

def refreshImage ():
	setCurrentSettings()
	os.system('rm current.jpg')
	url = 'http://192.168.178.124:8080/photo.jpg'
	wget.download(url, 'current.jpg');

def refreshAndSaveImage ():
    refreshImage()
    filename = int(time.time())
    os.system(f'cp current.jpg ./series/{filename}.jpg')
    print(f'Captured image {filename}.jpg')

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


