import time
from datetime import datetime, date, timedelta
import os
import sys
from pathlib import Path
from tqdm import tqdm

IMAGE_ROOT = './data'
image_dir = Path(IMAGE_ROOT)
if (image_dir.is_dir() == False):
	sys.exit(f'Cannot find folder "{IMAGE_ROOT}". Please make sure it exists.')

def getFolderForImage (imagePath):
	imageDate = date.fromtimestamp(int(imagePath.name[:-4]))
	foldername = imageDate.isoformat()
	folder = image_dir / foldername

	# Automatically create new folders
	if (folder.is_dir() == False):
		folder.mkdir()

	return folder

def ingestFile (pathToFile):
	destinationFolder = getFolderForImage(pathToFile)
	os.system(f'cp {str(pathToFile)} {str(destinationFolder)}')


FFMPEG_COMMAND = lambda cwd: f'ffmpeg -loglevel warning -hide_banner -nostats -pattern_type glob -i "{cwd}/*.jpg" -s 1920x1440 "{cwd}/output.mp4"'
def render_video_for_folder (folder):
	cwd = str(folder)
	os.system(FFMPEG_COMMAND(cwd))

# INGEST

ingestRoot = Path('/media/falk/rootfs/home/pi/tomato_cam/series')
filesToIngest = [f for f in ingestRoot.iterdir()]

for file in tqdm(filesToIngest, 'ingesting files'):
	try:
		ingestFile(file)
	except Exception as e:
		print(f'Something went wrong ingesting {str(file)}: {str(e)}!')

# RENDER

foldersToRender = [f for f in image_dir.iterdir() if (f.is_dir() and (f / 'output.mp4').is_file() == False)]
for folder in tqdm(foldersToRender, 'rendering timelapses'):
	try:
		render_video_for_folder(folder)
	except Exception as e:
		print(f'Something went wrong rendering {str(folder)}: {str(e)}!')


print(f'Successfully ingested {len(filesToIngest)} files and rendered {len(foldersToRender)} timelapses.')