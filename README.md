# Tomato Cam
**simple timelapse image acquisition**

#### Ideas - Dashboard v2
 - [ ] Option to disable flash
 - [ ] Display if flash was actually used on last image
 - [ ] Calendar view of recordings
 - [ ] Display free / used disk space
 - [ ] Quality of recording per day (images taken)
 - [ ] Quick render (render current day even if not complete)
 - [ ] More information (weather, temp)

#### General
 - [ ] Automatic oncatenation of videos for complete timelapse (http://trac.ffmpeg.org/wiki/Concatenate)
 - [ ] Detection of obstructed frames (during plant maintainance)
 - [ ] Normalization of image brightness ( -> max)
 	- [ ] Evaluation of image brightness over time (image metadata ISO, Exposure)
 - [ ] Calculate exposure using dynamic day length
 - [ ] Gradual exposure compensation (not just 0 and 4)
 - [ ] Script for automatated backup to external medium -> purge raw images, keep videos

#### Done
 - [x] Dashboard v1.0
 - [x] Automatic generation of daily videos (crop images (<- no); ffmpeg)
 - [x] New folder per day
 - [x] Move image acquisition to requests module
 - [x] Remove wget module
 - [x] Check for more default settings
