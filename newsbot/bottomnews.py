#!/usr/bin/env python
# bottomnews.py - Send the daily "Tagesschau in 100 Sekunden (auf Arabisch)"
# video to a WhatsApp group with refugees.

import datetime
import getopt
import os
import pprint
import re
import sys
from subprocess import call

import bs4
import requests


def main(argv):
    verbose = False

    try:
        options, remainder = getopt.getopt(argv, "v", "verbose")
    except getopt.GetoptError:
        print("Usage: " + os.path.basename(__file__) + " [-v] [--verbose]")
        print("")
        print("    -v, --verbose    suppress log output")
        print("")
        sys.exit(2)

    for opt, arg in options:
        if opt in ('-v', '--verbose'):
            verbose = True

    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    dayString = today.strftime("%m%d")
    yesterdayString = yesterday.strftime("%m%d")
    videoExtension = '.mp4'
    videoFolderName = '/home/*****/yowsup/newsbot/video'
    videoFileName = 'Tagesschau100sArabic'
    videoFileNameToday = videoFileName + dayString + videoExtension
    videoFileNameYesterday = videoFileName + yesterdayString + videoExtension
    videoFileTodayPath = videoFolderName + '/' + videoFileNameToday
    videoFileYesterdayPath = videoFolderName + '/' + videoFileNameYesterday

    player = requests.get('https://www.tagesschau.de/100s/arabisch/')

    try:
        player.raise_for_status()

        if not verbose:
            print('Got website. (https://www.tagesschau.de/100s/arabisch/)')
    except Exception as e:

        if not verbose:
            print('Error getting the website: %s' % (e))

    playerTextSoup = bs4.BeautifulSoup(player.text, "html.parser")
    videoLink = playerTextSoup.findAll(href=re.compile('websm.h264.mp4'))
    videoHref = videoLink[0].get('href')
    video = requests.get(videoHref)

    try:
        video.raise_for_status()

        if not verbose:
            print('Got video. (' + videoHref + ')')
    except Exception as e:

        if not verbose:
            print('Error getting the video: %s' % (e))

    if not os.path.exists(videoFolderName):
        os.makedirs(videoFolderName)

        if not verbose:
            print('Created video directory. (' + videoFolderName + ')')

    if os.path.isfile(videoFileYesterdayPath):
        os.remove(videoFileYesterdayPath)

        if not verbose:
            print('Removed old video. (' + videoFileYesterdayPath + ')')

    if not os.path.isfile(videoFileTodayPath):
        videoFile = open(videoFileTodayPath, 'wb')

        for chunk in video.iter_content(100000):
            videoFile.write(chunk)

        videoFile.close()

        if not verbose:
            print('Wrote video. (' + videoFileTodayPath + ')')
            print('Connecting to WhatsApp ...')

    today = datetime.date.today()
    commandlist = ["/home/*****/yowsup/yowsup-newsbot.py", "demos", "--news",
                   today.strftime('%m.%d.%Y'), "--config",
                   "/home/*****/yowsup/config"]

    if verbose:
        commandlist.append("--verbose")

    call(commandlist)

if __name__ == "__main__":
    main(sys.argv[1:])
