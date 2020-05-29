const fs = require('fs').promises;
const { createWriteStream } = require('fs');
const http = require('http');

const { promisify } = require('util');
const exec = promisify(require('child_process').exec);

// ----------- CONFIGURATION ----------------------------
const IMAGE_HOST = `http://192.168.178.124:8080`;
const URL_SETTINGS =  `${IMAGE_HOST}/settings`;
const URL_IMAGE = `${IMAGE_HOST}/photo.jpg`;

const IMAGE_ROOT = './data';
const HTTP_PORT = 3000;

const DEFAULT_SETTINGS = {
	'flashmode': 'auto',
	'focusmode': 'infinity',
	'whitebalance': 'cloudy-daylight'
};

// ---------------- TIMELAPSE ------------------------------

// IIFE (immediately invoked function expression) allows tighter scoping of variables
// let a = (function () { return 2 }());
// a == 2
const renderVideoInFolder = (function () {
	const FFMPEG_COMMAND = cwd => `ffmpeg -loglevel warning -hide_banner -nostats -pattern_type glob -i "${cwd}/*.jpg" -s 1920x1440 "${cwd}/output.mp4"`;

	// This is the actual value for renderVideoInFolder
	return async folderPath => {
		console.log('Rendering timelapse for ', folderPath);
		await exec(FFMPEG_COMMAND(folderPath))
		console.log('Finished rendering timelapse.')
	};
}());

// -------------- FILES ----------------------------------
const utils = (function () {
	// Adds this function to every Date() object
	Date.prototype.toISODateString = function () {
		// This is an inline function with an inline conditional expression.
		const pad = x => x < 10 ? ('0' + x) : x;
		return this.getUTCFullYear() +
	        '-' + pad(this.getUTCMonth() + 1) +
	        '-' + pad(this.getUTCDate());
	};

	const isDir = async (path) => {
		try {
			const stat = await fs.lstat(path);
			return stat.isDirectory() || stat.isSymbolicLink();
		} catch (error) {
			return false;
		}
	};

	const isFile = async (path) => {
		try {
			const stat = await fs.lstat(path);
			return stat.isFile() || stat.isSymbolicLink();
		} catch (error) {
			return false;
		}
	}

	return { isDir, isFile };
}());

const getImagePath = (function () {
	const getFolderPathForDate = async (date, create = true) => {
		const folderName = date.toISODateString();
		const folderPath = IMAGE_ROOT + '/' + folderName;

		// Automatically create new folders
		if (await utils.isDir(folderPath) === false) {
			await fs.mkdir(folderPath);

			const nameYesterday = (function () {
				const d = new Date(date.getTime());
				d.setDate (d.getDate() -1);
				return d.toISODateString();
			}());
			const pathYesterday = IMAGE_ROOT + '/' + nameYesterday;

			if (await utils.isDir(pathYesterday) === true) {
				await event__dayFinished(pathYesterday);
			}
		}

		return folderPath;
	};

	const checkImageDir = async () => {
		if (await utils.isDir(IMAGE_ROOT) === false) {
			console.error(`Cannot find image root ${IMAGE_ROOT}. Please make sure it exists.`);
			process.exit(1);
		}
	};

	// Make sure the image root exists
	checkImageDir();

	// This is the value for getImagePath
	return async () => {
		const now = new Date();
		const folderPath = await getFolderPathForDate(now);
		return folderPath + `/${parseInt(now.getTime() / 1000)}.jpg`;
	};
}());

// -------------- IMAGE ACQUISITION --------------------
const httpAPI = (function () {
	const downloadFile = (url, destPath) => {
		// Promises are the underlying magic of async/await and are basically just very fancy callbacks.
		// See https://javascript.info/async for an introduction
		return new Promise((resolve, reject) => {
			const fileStream = createWriteStream(destPath, { autoClose: true });
			const request = http.get(url, (response) => {
				if (response.statusCode !== 200) {
					reject(`HTTP request failed with ${response.statusCode}`);
				}

				response.pipe(fileStream);
			});

			const handleError = err => fs
	        	.unlink(destPath)
	        	.finally(() => reject(err.message));

		    request.on('error', handleError);
		    fileStream.on('error', handleError);
		    fileStream.on('finish', resolve);
		});
	};

	const makeRequest = (url) => {
		return new Promise((resolve, reject) => {
			const request = http.get(url, (response) => {
				if (response.statusCode !== 200) {
					reject(`HTTP request failed with ${response.statusCode}`);
				} else {
					resolve() // We ignore the response data
				}
			});
			request.on('error', err => reject(err.message));
		});
	};

	// This is the value for httpAPI
	return { downloadFile, makeRequest };
}());



// -------------- EVENTS ----------------------------------
const event__dayFinished = async folderPath => {
	console.log('New day started!');
	renderVideoInFolder(folderPath); // Don not wait for completion
};

let lastImageTimestamp = 0
const event__newImageCaptured = async filename => {
	lastImageTimestamp = parseInt(Date.now() / 1000);
	console.log('New image captured: ', filename);
};

// ------------------- LOGIC ---------------------------
const getCurrentSettings = () => {
	const hourNow = new Date().getHours();
	return {
		...DEFAULT_SETTINGS,
		exposure: (hourNow < 6 || hourNow > 21) ? 4 : 0
	};
}

const setCurrentSettings = async () => {
	const settings = getCurrentSettings()
	for (let key in settings) {
		await httpAPI.makeRequest(`${URL_SETTINGS}/${key}?set=${settings[key]}`);
	}
};

const refreshImage = async () => {
	await setCurrentSettings();
	await httpAPI.downloadFile(URL_IMAGE, './current.jpg');
};

const refreshAndSaveImage = async () => {
	await refreshImage();
	const imagePath = await getImagePath();

	await exec(`cp ./current.jpg ${imagePath}`);
	await event__newImageCaptured(imagePath);
};

// Capture 20 images per hour | ~28GB per month at 2MB per image
// setInterval(refreshAndSaveImage, 3 * 60 * 1000);



// --------------------------- HTTP SERVER -------------------------------------
const httpServerAPI = (function () {
	const getInfo = () => {
		return {
			lastImageTimestamp,
			settings: getCurrentSettings()
		};
	};

	const getDays = async () => {
		const dirEntries = await fs.readdir(IMAGE_ROOT, { withFileTypes: true });

		const days = [];
		for (let dirEntry of dirEntries) {
			if (dirEntry.isDirectory()) {
				const dirPath = `${IMAGE_ROOT}/${dirEntry.name}`;

				const numOfImages = (await fs.readdir(dirPath)).length;
				const hasVideo = await utils.isFile(`${dirPath}/output.mp4`);

				days.push({
					date: dirEntry.name,
					hasVideo,
					numOfImages
				});
			}
		};

		return days;
	};

	return { getInfo, getDays };
}());


const express = require('express');
const app = express();

app.get('/days', async (req, res, next) => {
	const days = await httpServerAPI.getDays();
	return res.json(days);
});
app.get('/info', async (req, res, next) => {
	const info = await httpServerAPI.getInfo();
	return res.json(info);
});
app.use(express.static('.'));

app.listen(HTTP_PORT, () => console.log(`tomato-cam listening on port ${HTTP_PORT}.`));
