# Write your code here :-)
#!/usr/bin/python
# -*- coding:utf-8 -*-

#original VSMP by Bryan Boyer, https://medium.com/s/story/very-slow-movie-player-499f76c48b62
#this implementation was adapted from Tom Whitwell's version, https://medium.com/@tomwhitwell/how-to-build-a-very-slow-movie-player-in-2020-c5745052e4e4

import os, time, sys, random
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), '/home/pi/code/eink-test/lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from PIL import Image,ImageDraw,ImageFont
import ffmpeg
import logging, traceback
from waveshare_epd import epd2in7
import argparse

def generate_frame(in_filename, out_filename, time, width):
    (
        ffmpeg
        .input(in_filename, ss=time)
        #this filter flips the video 90 deg countercloclwise
        .filter('transpose', 2)
        .filter('scale', width, -1)
        .filter('pad',width,height,-1,-1)
        .output(out_filename, vframes=1)
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )


viddir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '/home/pi', 'Videos/')

logging.basicConfig(level=logging.DEBUG)

epd = epd2in7.EPD()

logging.info("init and clear")
epd.init()
epd.Clear(0xFF)

def check_mp4(value):
    if not value.endswith('.mp4'):
        raise argparse.ArgumentTypeError("%s should be an .mp4 file" % value)
    return value

parser = argparse.ArgumentParser(description='SlowMovie Settings')
parser.add_argument('-r', '--random', action='store_true',
    help="Random mode: chooses a random frame every refresh")
parser.add_argument('-f', '--file', type=check_mp4,
    help="Add a filename to start playing a specific film. Otherwise will pick a random file, and will move to another film randomly afterwards.")
parser.add_argument('-d', '--delay',  default=120,
    help="Delay between screen updates, in seconds")
parser.add_argument('-i', '--inc',  default=1,
    help="Number of frames skipped between screen updates")
parser.add_argument('-s', '--start',
    help="Start at a specific frame")
args = parser.parse_args()

currentSessionCounter = 0

while 1:
    if args.file:
        print ("playing requested mp4 %s" %args.file)
        inputVid = viddir + args.file;
    else:
        print("playing default video, This Is Coffee!")
        inputVid = viddir + "ThisisCo1961_512kb.mp4"
    print(inputVid)

    width = epd.width
    height = epd.height

    #check how many frames are in the movie
    frameCount = int(ffmpeg.probe(inputVid)['streams'][0]['nb_frames'])

    if args.random:
        print("random mode")
        #pick a random frame
        frame = random.randint(0,frameCount)
    else:
        print("playthrough mode")

        #if there's a start frame in arguments, write that first
        if currentSessionCounter == 0:
            if args.start:
                frameMemory = open(os.path.join('/home/pi/code/eink-test/assets', 'frame.txt'), 'w');
                if frameMemory.mode == 'w':
                    frameMemory.write(str(args.start))
                frameMemory.close()

        #load frame from .txt file
        frameMemory = open(os.path.join('/home/pi/code/eink-test/assets', 'frame.txt'), 'r');
        if frameMemory.mode == 'r':
            frame = int(frameMemory.read())
        frameMemory.close()

        #figure out next frame, loop back if you get to the end
        frameInc = int(frame) + int(args.inc)
        if frameInc > frameCount:
            nextFrame = 0
            print("looped back to beginning!")
        else :
            nextFrame = frameInc

        #advance frame by whatever args are around
        frameMemory = open(os.path.join('/home/pi/code/eink-test/assets', 'frame.txt'), 'w');
        if frameMemory.mode == 'w':
            frameMemory.write(str(nextFrame))
        frameMemory.close()
        print("increment by %s frames" %args.inc)


    #wait for 10 seconds

    #convert that frame to timecode
    msTimecode = "%dms"%(frame*41.666666)

    #use ffmpeg to extract a frame from the movie, crop it, letterbox it, and save it as grab.jpg
    generate_frame(inputVid, 'grab.jpg', msTimecode, width)

    #open grab.jpg in PIL
    pil_im = Image.open('grab.jpg')

    #dither!
    pil_im = pil_im.convert(mode='1',dither=Image.FLOYDSTEINBERG)

    #display the dithered image
    epd.display(epd.getbuffer(pil_im))
    print('Displaying frame %d of %s' %(frame,inputVid))

    currentSessionCounter+=1

    if args.delay:
        print("delay by %s seconds" %args.delay)
        time.sleep(int(args.delay))
    else:
        print("delay by default 120s")
        time.sleep(120)

epd.sleep()
epd2in7.epdconfig.module_exit()
exit()