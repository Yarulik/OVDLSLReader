import numpy, sys, os

# retrieve LSL library compiled by OpenViBE
# FIXME: not working??
ov_lib_path = os.getcwd() + "/../dependencies/lib/"
sys.path.append(ov_lib_path)

# FIXME absolute path to point to pylsl.py
sys.path.append("/home/jfrey/bluff_game/ov_lsl/lib")

from pylsl import StreamInlet, resolve_stream

class MyOVBox(OVBox):
   """
   Embedding LSL reading within a python box
   """
   def __init__(self):
      OVBox.__init__(self)
      self.channelCount = 0
      self.samplingFrequency = 0
      self.epochSampleCount = 0
      self.minValue = 0
      self.startTime = 0.
      self.endTime = 0.
      self.dimensionSizes = list()
      self.dimensionLabels = list()
      self.timeBuffer = list()
      self.signalBuffer = None
      self.signalHeader = None
      
   # this time we also re-define the initialize method to directly prepare the header and the first data chunk
   def initialize(self):           
      # settings are retrieved in the dictionary
      self.samplingFrequency = int(self.setting['Sampling frequency'])
      self.epochSampleCount = int(self.setting['Generated epoch sample count'])
      self.stream_type=self.setting['Stream type']
      
      
      # total channels for all streams
      self.channelCount = 0
      
      print "Looking for streams of type: " + self.stream_type

      streams = resolve_stream('type',self.stream_type)
      self.nb_streams = len(streams)
      print "Nb streams: " + str(self.nb_streams)

      # create inlets to read from each stream
      self.inlets = []
      # retrieve also corresponding StreamInfo for future uses (eg sampling rate)
      self.infos = []
      
      for stream in streams:
        inlet = StreamInlet(stream)
        self.inlets.append(inlet)
        info = inlet.info()
        print "Stream: " + info.name()
        self.infos.append(info)
        print "Nb channels: " + str(info.channel_count())
        self.channelCount += info.channel_count()
        
      self.values =  self.channelCount*[0]
      
      #creation of the signal header
      for i in range(self.channelCount):
        self.dimensionLabels.append('Min value') 
        
      self.dimensionLabels += self.epochSampleCount*['']
      self.dimensionSizes = [self.channelCount, self.epochSampleCount]
      self.signalHeader = OVSignalHeader(0., 0., self.dimensionSizes, self.dimensionLabels, self.samplingFrequency)
      self.output[0].append(self.signalHeader)

      #creation of the first signal chunk
      self.endTime = 1.*self.epochSampleCount/self.samplingFrequency
      self.signalBuffer = numpy.zeros((self.channelCount, self.epochSampleCount))
      self.updateTimeBuffer()
      self.updateSignalBuffer()
      print "end init"
      

   def updateFromGUI(self):
     print "updateFromGUI"
     cur_chan = 0
     for i in range(self.nb_streams):
       inlet = self.inlets[i]
       info = self.infos[i]
       nb_channels = info.channel_count()
       # fill values with each channel
       sample,timestamp = inlet.pull_sample()
       print "feed: " + str(i),
       print sample	 
       self.values[cur_chan:cur_chan+nb_channels] = sample
       cur_chan += nb_channels
     
   def updateStartTime(self):
      self.startTime += 1.*self.epochSampleCount/self.samplingFrequency

   def updateEndTime(self):
      self.endTime = float(self.startTime + 1.*self.epochSampleCount/self.samplingFrequency)

   def updateTimeBuffer(self):
      print "updateTimeBuffer"
      self.timeBuffer = numpy.arange(self.startTime, self.endTime, 1./self.samplingFrequency)

   def updateSignalBuffer(self):
     print "updateSignalBuffer"
     for i in range(self.channelCount):
       value = self.values[i]
       print "value for " + str(i) + ": ",
       print value
       self.signalBuffer[i,:] = value
       print "buffer:",
       print self.signalBuffer[i]
       print "ok"

   def sendSignalBufferToOpenvibe(self):
      start = self.timeBuffer[0]
      end = self.timeBuffer[-1] + 1./self.samplingFrequency
      bufferElements = self.signalBuffer.reshape(self.channelCount*self.epochSampleCount).tolist()
      self.output[0].append( OVSignalBuffer(start, end, bufferElements) )

   # the process is straightforward
   def process(self):
      print "process"
      start = self.timeBuffer[0]
      print "start: " + str(start)
      end = self.timeBuffer[-1]
      print "end: " + str(end)
      if self.getCurrentTime() >= end:
	 print "in condition"
         # retrieve values
         self.updateFromGUI()
         # deal with data
         self.sendSignalBufferToOpenvibe()
         self.updateStartTime()
         self.updateEndTime()
         self.updateTimeBuffer()
         self.updateSignalBuffer()
      print "end process"

   # re-define the uninitialize method to output the end chunk + close streams
   def uninitialize(self):
      print "uninit"
      for inlet in self.inlets:
        inlet.close_stream()
      end = self.timeBuffer[-1]
      self.output[0].append(OVSignalEnd(end, end))
      
      
box = MyOVBox()
