import numpy
from Tkinter import *

# Compute IBI (for HRV, in seconds) and BPM using stimulations (any type), primery use for heart
# FIXME: all values for one buffer and channel are identical

class MyOVBox(OVBox):
   def __init__(self):
      OVBox.__init__(self)
      self.channelCount = 0
      self.samplingFrequency = 0
      self.epochSampleCount = 0 # should be a divider of self.timeBuffer!
      self.curEpoch = 0
      self.startTime = 0.
      self.endTime = 0.
      self.dimensionSizes = list()
      self.dimensionLabels = list()
      self.timeBuffer = list()
      self.signalBuffer = None
      self.signalHeader = None
      self.BPMvalue = 60.
      self.realBPM = self.BPMvalue
      self.IBIvalue = 1./self.BPMvalue*60
      # Code if a beat is detected / produced
      # -1: no beat
      # 1: from external stim
      # 2: guard too long
      # 3: guard too short
      self.beatValue = -1
      self.lastStimDate = 0
      self.newStimDate = 0
      self.lastBeatDate = 0
      self.debug = False

   # this time we also re-define the initialize method to directly prepare the header and the first data chunk
   def initialize(self):
      # one channel for IBI, another for BPM, last for beat
      self.channelCount = 3
      
      # try get debug flag from GUI
      try:
        debug = (self.setting['Debug']=="true")
      except:
        print "Couldn't find debug flag"
      else:
        self.debug=debug
        
      # settings are retrieved in the dictionary
      self.samplingFrequency = int(self.setting['Sampling frequency'])
      self.epochSampleCount = int(self.setting['Generated epoch sample count'])
      
      # safeguards (-1 to disable)
      self.minBPM = int(self.setting['Min BPM'])
      self.maxBPM = int(self.setting['Max BPM'])
      # BPM variation between two seconds
      self.maxVariation = int(self.setting['Max variation'])
         
      #creation of the signal header
      self.dimensionLabels.append('IBI') 
      self.dimensionLabels.append('BPM')
      self.dimensionLabels.append('beat') 
      self.dimensionLabels += self.epochSampleCount*['']
      self.dimensionSizes = [self.channelCount, self.epochSampleCount]
      self.signalHeader = OVSignalHeader(0., 0., self.dimensionSizes, self.dimensionLabels, self.samplingFrequency)
      self.output[0].append(self.signalHeader)

      #creation of the first signal chunk
      self.endTime = 1.*self.epochSampleCount/self.samplingFrequency
      self.signalBuffer = numpy.zeros((self.channelCount, self.epochSampleCount))
      self.updateTimeBuffer()
      self.resetSignalBuffer()
    
   def updateStartTime(self):
      self.startTime += 1.*self.epochSampleCount/self.samplingFrequency

   def updateEndTime(self):
      self.endTime = float(self.startTime + 1.*self.epochSampleCount/self.samplingFrequency)

   def updateTimeBuffer(self):
      self.timeBuffer = numpy.arange(self.startTime, self.endTime, 1./self.samplingFrequency)

   # fill buffer upon new epoch
   def resetSignalBuffer(self):
      self.signalBuffer[0,:] = self.IBIvalue
      self.signalBuffer[1,:] = self.BPMvalue
      self.signalBuffer[2,:] = -1

   def sendSignalBufferToOpenvibe(self):
      start = self.timeBuffer[0]
      end = self.timeBuffer[-1] + 1./self.samplingFrequency
      bufferElements = self.signalBuffer.reshape(self.channelCount*self.epochSampleCount).tolist()
      self.output[0].append( OVSignalBuffer(start, end, bufferElements) )


   # called by process for each stim reiceived; update timestamp of last stim
   def trigger(self, stim):
     if self.debug:
       print "Got stim: ", stim.identifier, " date: ", stim.date, " duration: ", stim.duration
     self.newStimDate = stim.date
   
   # called by process each loop or by trigger when got new stimulation;  update IBI/BPM
   def updateValues(self):
     trueBeat = False # remember genuine beat for beatValue
     # a new beat has beat triggered
     if self.newStimDate != self.lastStimDate:
       self.realBPM = 1./(self.newStimDate - self.lastStimDate)*60
       self.lastStimDate = self.newStimDate
       trueBeat = True
     # crossed IBI, real BPM starts to decrease
     elif self.lastStimDate + 1./self.realBPM*60 < self.getCurrentTime():
       self.realBPM = 1./(self.getCurrentTime() - self.lastStimDate)*60
     # set bottom/top BPM depending on variation
     newBPMslow = self.realBPM
     newBPMfast = self.realBPM
     if self.maxVariation >=0:
       # using time since last beat to make BPM crops linear
       lapse = self.getCurrentTime() - self.lastBeatDate
       newBPMslow = self.BPMvalue - self.maxVariation * lapse
       newBPMfast = self.BPMvalue + self.maxVariation * lapse
     # safeguards for min/max
     if newBPMslow < 0:
       newBPMslow = 0
     if newBPMslow < self.minBPM:
       newBPMslow = self.minBPM
     if newBPMslow > self.maxBPM:
       newBPMslow = self.maxBPM
     if newBPMfast < self.minBPM:
       newBPMfast = self.minBPM
     if newBPMfast > self.maxBPM:
       newBPMfast = self.maxBPM
       
     if self.debug:
       print "oldBPM: ", self.BPMvalue,", realBPM: ", self.realBPM, ", newBPMslow: ", newBPMslow, " newBPMfast: ", newBPMfast
     
     # safeguard too fast, will wait for right time before a fake beat is produced
     if self.realBPM > newBPMfast and newBPMfast>0:
        if self.debug:
          print "too fast"
        nextBeatDate = self.lastBeatDate + 60./newBPMfast
        if self.getCurrentTime() >= nextBeatDate:
          self.lastBeatDate = self.getCurrentTime()
          self.BPMvalue = newBPMfast
          if self.debug:
            print "correct fast"
          self.beatValue = 3
     # real beat in there, inside variation
     elif self.realBPM >= newBPMslow:
       if trueBeat:
         self.lastBeatDate = self.newStimDate
         self.BPMvalue = self.realBPM
         self.beatValue = 1
         if self.debug:
           print "real beat"
     # safeguard too slow
     elif self.getCurrentTime() - self.lastBeatDate >= 1./newBPMslow*60:
       self.BPMvalue = newBPMslow
       self.lastBeatDate = self.getCurrentTime()
       if self.debug:
         print "correct slow"
       self.beatValue = 2
     
     # update internal state
     if self.BPMvalue != 0:
       self.IBIvalue = 1./self.BPMvalue*60
     else:
       self.IBIvalue = 0
     self.signalBuffer[0,self.curEpoch:] = self.IBIvalue
     self.signalBuffer[1,self.curEpoch:] = self.BPMvalue
     self.signalBuffer[2,self.curEpoch] = self.beatValue # value only for a beat

   # the process is straightforward
   def process(self):
      ## Deal with received stimulations
      # we iterate over all the input chunks in the input buffer
      for chunkIndex in range( len(self.input[0]) ):
         # if it's a header... we have to catch it otherwise it'll be seen as OVStimulationSet (??), but that's it
         if(type(self.input[0][chunkIndex]) == OVStimulationHeader):
           self.input[0].pop()
         # we reiceive actual data
         elif(type(self.input[0][chunkIndex]) == OVStimulationSet):
           # create a list for corresponding chunck
           stimSetIn = self.input[0].pop()
           # even without any signals we receive sets, have to check what they hold
           nb_stim =  str(len(stimSetIn))
           for stim in stimSetIn:
             # check which 
             self.trigger(stim)
         # useless?
         elif(type(self.input[0][chunkIndex]) == OVStimulationEnd):
           self.input[0].pop()
           
      # in case we need to automatically change BPM 'cause of min/max
      self.updateValues()
      
      # update timestamps
      start = self.timeBuffer[0]
      end = self.timeBuffer[-1]
      while self.curEpoch < self.epochSampleCount and self.getCurrentTime() >= self.timeBuffer[self.curEpoch]:
         self.curEpoch+=1
         self.beatValue = -1
      # send IBI & BPM values      
      if self.getCurrentTime() >= end:
         # send buffer
         self.sendSignalBufferToOpenvibe()
         self.updateStartTime()
         self.updateEndTime()
         self.updateTimeBuffer()
         self.resetSignalBuffer()
         self.curEpoch = 0

   # this time we also re-define the uninitialize method to output the end chunk.
   def uninitialize(self):
      end = self.timeBuffer[-1]
      self.output[0].append(OVSignalEnd(end, end))

box = MyOVBox()
