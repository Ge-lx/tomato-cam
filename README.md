# Tomato Cam
**simple timelapse image acquisition**

 - Move image acquisition to requests module
 - Remove wget module

 - Calculate exposure using dynamic day length
 - Gradual exposure compensation (not just 0 and 4)
 - Check for more default settings

 - Dashboard ?
 - Automatic generation of daily videos (crop images; ffmpeg)
 - New folder per day / different naming scheme: more then just the timestamp in filename
 	- Might be needed to generate videos automatically (and generally quite convenient)

 - Detection of obstructed frames (during plant maintainance)
 - Normalization of image brightness ( -> max)
