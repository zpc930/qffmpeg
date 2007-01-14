#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import os
import sys
from subprocess import *
from PyQt4.QtCore import *

def showHelp():
    print 'Usage: vivica -i input -t title'
    sys.exit(1)

class ProgressBar:
    def __init__(self, minValue = 0, maxValue = 100, totalWidth=50):
        self.progBar = "[]"   # This holds the progress bar string
        self.min = minValue
        self.max = maxValue
        self.span = maxValue - minValue
        self.width = totalWidth
        self.amount = 0       # When amount == max, we are 100% done
        self.text = ""

        self.updateAmount(0)  # Build progress bar string


    def setText(self,text):
        self.text = text

    def updateAmount(self, newAmount = 0):
        if newAmount < self.min: newAmount = self.min
        if newAmount > self.max: newAmount = self.max
        self.amount = newAmount

        # Figure out the new percent done, round to an integer
        diffFromMin = float(self.amount - self.min)
        percentDone = (diffFromMin / float(self.span)) * 100.0
        percentDone = round(percentDone)
        percentDone = int(percentDone)

        # Figure out how many hash bars the percentage should be
        allFull = self.width - 2
        numHashes = (percentDone / 100.0) * allFull
        numHashes = int(round(numHashes))

        # build a progress bar with hashes and spaces
        self.progBar = "%s[" % self.text + '#'*numHashes + ' '*(allFull-numHashes) + "]"

        # figure out where to put the percentage, roughly centered
        percentPlace = (len(self.progBar) / 2) - len(str(percentDone)) + len(self.text)/2
        percentString = str(percentDone) + "%"

        # slice the percentage into the bar
        self.progBar = self.progBar[0:percentPlace] + percentString + self.progBar[percentPlace+len(percentString):]

    def __str__(self):
        return str(self.progBar)

class QFFEncoder(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.bitrate = 0
        self.duration = 0
        self.parseBitrate = False
        self.parseDuration = False
        self.input = ""
        self.title = ""
        self.progress = ProgressBar()

        self.analyzeProc = QProcess(self)
        self.encodingProc = QProcess(self)

        self.connect(self.analyzeProc,SIGNAL("readyReadStandardError()"),self.identifyOutput)
        self.connect(self.analyzeProc,SIGNAL("finished(int)"),self.encodeFile)

        self.connect(self.encodingProc,SIGNAL("readyReadStandardError()"),self.parseOutput)
        self.connect(self.encodingProc,SIGNAL("finished(int)"),self.cleanup)

    def analyzeFile(self,input_file,title):
        self.input = input_file
        self.title = title

        self.analyzeProc.start('ffmpeg',['-i',unicode(self.input)])

    def identifyOutput(self):
        data = self.analyzeProc.readAllStandardError()

        if self.parseDuration:
            time_array = data.split(":")
            self.duration = time_array[2].toInt()[0] + 60*time_array[1].toInt()[0] + 60*60*time_array[0].toInt()[0]
            self.parseDuration = False
        elif self.parseBitrate:
            self.bitrate = data.split(" ")[0]
            self.parseBitrate = False

        if data.contains("Duration"):
            self.parseDuration = True
        elif data.contains("bitrate"):
            self.parseBitrate = True

    def parseOutput(self):
        data = self.encodingProc.readAllStandardError()
        regex = QRegExp("time=(\S+)")
        pos = 0

        pos = regex.indexIn(QString(data),pos)
        if pos != -1:
            self.progress.updateAmount((float(regex.cap(1))/float(self.duration))*100)
            print self.progress,"\r",

    def encodeFile(self):
        if self.bitrate >= 1500:
            bitrate = "1500k"
        else:
            bitrate = str(self.bitrate)+"k"

        self.analyzeProc.close()
        self.progress.setText("Encoding %s " % self.title)

        try:
            self.encodingProc.start('ffmpeg',['-y',
                                              '-i',unicode(input_file),
                                              '-acodec','aac',
                                              '-ac', '2',
                                              '-ab', '160k',
                                              '-s','640x480',
                                              '-vcodec', 'h264',
                                              '-b', bitrate,
                                              '-flags', '+loop',
                                              '-chroma', '1',
                                              '-partitions', '+parti4x4+partp4x4+partp8x8+partb8x8',
                                              '-me_method', '8',
                                              '-subq', '7',
                                              '-trellis', '2',
                                              '-refs', '1',
                                              '-coder', '0',
                                              '-me_range', '16',
                                              '-g', '300',
                                              '-bf', '0',
                                              '-keyint_min', '25',
                                              '-sc_threshold', '40',
                                              '-i_qfactor', '0.71',
                                              '-bt', '1500k',
                                              '-maxrate', '1OM',
                                              '-bufsize', '10M',
                                              '-rc_eq', "blurCplx^(1-qComp)",
                                              '-qcomp', '0.6',
                                              '-qmin', '10',
                                              '-qmax', '51',
                                              '-qdiff', '4',
                                              '-level', '30',
                                              "%s.tmp.mp4" % title])
        except KeyboardInterrupt:
            self.encodingProc.kill()

    def cleanup(self):
        self.encodingProc.close()

        # Remove output file if it already exists
        try:
            os.unlink("%s.mp4" % self.title)
        except OSError:
            pass

        # Mux with mp4box for iTunes
        Popen(['mp4box','-itags',"Name=%s:Encoder=FFmpeg" % self.title,'-ipod','-add', "%s.tmp.mp4" % self.title, "%s.mp4" % self.title]).communicate()

        # Remove temp file
        try:
            os.unlink("%s.tmp.mp4" % self.title)
        except OSError:
            pass

        print "Now you can transfer %s.mp4 to your iPod. Have fun!" % self.title

if __name__ == "__main__":
    app = QCoreApplication(sys.argv)
    encoder = QFFEncoder()
    input_file = ""
    title = ""

    try:
        opts, args = getopt.getopt(sys.argv[1:],"i:t:h",["input:","title=","help"])
        for opt, arg in opts:
            if opt in ("-h","--help"):
                showHelp()
            elif opt in ("-t","--title"):
                title = arg
            elif opt in ("-i","--input"):
                input_file = arg

        if not input_file:
            showHelp()
        elif not title:
            title = (input_file.split('/')[-1]).split('.')[0]

        encoder.analyzeFile(input_file,title)
        app.exec_()

    except getopt.GetoptError:
        sys.exit(1)
