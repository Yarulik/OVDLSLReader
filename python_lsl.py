import numpy, sys, os
from math import ceil
# retrieve LSL library compiled by OpenViBE
# FIXME: not working??
ov_lib_path = os.getcwd() + "/../dependencies/lib/"
sys.path.append(ov_lib_path)

# FIXME absolute path to point to pylsl.py
sys.path.append("/home/jfrey/bluff_game/ov_lsl/lib")

from pylsl import StreamInlet, resolve_stream

class MyOVBox(OVBox):
   """
   Embedding LSL reading within a python box.
   WARNING: the resolution order of streams is random, ie constant order is not guaranteed
   WARNING: in case a specific stream name is target, will retain the first match found
   NB: if "Sampling frequency" is set, then will force value for all streams, otherwise will select frequency reported by first one and apply it to all
   """
   def __init__(self):
      OVBox.__init__(self)
      self.channelCount = 0
      self.samplingFrequency = 0
      self.epochSampleCount = 0
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
      try:
        self.samplingFrequency = int(self.setting['Sampling frequency'])
      except:
        print "Sampling frequency not set or error while parsing."
        self.samplingFrequency = 0
      print "Sampling frequency: " + str(self.samplingFrequency)
      self.epochSampleCount = int(self.setting['Generated epoch sample count'])
      self.stream_type=self.setting['Stream type']
      # total channels for all streams
      self.channelCount = 0
      
      all_streams = self.setting['Get all streams'] == "true"
      self.stream_name=self.setting['Stream name'] # in case !all_streams
      
      print "Looking for streams of type: " + self.stream_type
      
      streams = resolve_stream('type',self.stream_type)
      print "Nb streams: " + str( len(streams))
      
      if not all_streams:
        print "Will only select (first) stream named: " + self.stream_name
        self.nb_streams = 1
      else:
        self.nb_streams = len(streams)

      # create inlets to read from each stream
      self.inlets = []
      # retrieve also corresponding StreamInfo for future uses (eg sampling rate)
      self.infos = []
      
      # save inlets and info + build signal header
      for stream in streams:
        inlet = StreamInlet(stream)
        info = inlet.info()
        name = info.name()
        print "Stream name: " + name
        # if target one stream, ignore false ones
        if not all_streams and name != self.stream_name:
          continue
        print "Nb channels: " + str(info.channel_count())
        self.channelCount += info.channel_count()
        stream_freq = info.nominal_srate()
        print "Sampling frequency: " + str(stream_freq)
        if self.samplingFrequency == 0:
          print "Set sampling frequency to:" + str(stream_freq)
          self.samplingFrequency = stream_freq
        elif self.samplingFrequency != stream_freq:
          print "WARNING: sampling frequency of current stream (" + str(stream_freq) + ") differs from option set to box (" + str(self.samplingFrequency) + ")."
        for i in range(info.channel_count()):
          self.dimensionLabels.append(name + ":" + str(i))
          
        # We must delay real inlet/info init because we may know the defifitive sampling frequency
        # limit buflen just to what we need to fill each chuck, kinda drift correction
        # TODO: not a very pretty code...
        buffer_length = int(ceil(float(self.epochSampleCount) / self.samplingFrequency))
        print "LSL buffer length: " + str(buffer_length)
        inlet = StreamInlet(stream, max_buflen=buffer_length)
        info = inlet.info()
        self.inlets.append(inlet)
        self.infos.append(info)
        
        # if we're still here when we target a stream, it means we foand it
        if not all_streams:
          print "Found target stream"
          break
 
      # we need at least one stream before we let go
      if self.channelCount <= 0:
        raise Exception("Error: no stream found.")
      
      # backup last values pulled in case pull(timeout=0) return None later
      self.last_values =  self.channelCount*[0]
      
      self.dimensionLabels += self.epochSampleCount*['']
      self.dimensionSizes = [self.channelCount, self.epochSampleCount]
      self.signalHeader = OVSignalHeader(0., 0., self.dimensionSizes, self.dimensionLabels, self.samplingFrequency)
      self.output[0].append(self.signalHeader)

      #creation of the first signal chunk
      self.endTime = 1.*self.epochSampleCount/self.samplingFrequency
      self.signalBuffer = numpy.zeros((self.channelCount, self.epochSampleCount))
      self.updateTimeBuffer()
      self.updateSignalBuffer()
        
   def updateStartTime(self):
      self.startTime += 1.*self.epochSampleCount/self.samplingFrequency

   def updateEndTime(self):
      self.endTime = float(self.startTime + 1.*self.epochSampleCount/self.samplingFrequency)

   def updateTimeBuffer(self):
      self.timeBuffer = numpy.arange(self.startTime, self.endTime, 1./self.samplingFrequency)

   def updateSignalBuffer(self):
     # read XX times each channel to fill chunk
     cur_chan = 0
     for i in range(self.nb_streams):
       inlet = self.inlets[i]
       info = self.infos[i]
       nb_channels = info.channel_count()
       for j in range(self.epochSampleCount):
         # fill values with each channel -- timeout 0 so may have duplicate
         sample,timestamp = inlet.pull_sample(timeout=0)
         # update value only if got new ones
         if sample != None:
           #print "new values"
           self.last_values[cur_chan:cur_chan+nb_channels] = sample
           self.signalBuffer[cur_chan:cur_chan+nb_channels, j] = sample
         # else fetch values from memory if no new
         else:
           self.signalBuffer[cur_chan:cur_chan+nb_channels, j] =  self.last_values[cur_chan:cur_chan+nb_channels]
       cur_chan += nb_channels

   def sendSignalBufferToOpenvibe(self):
      start = self.timeBuffer[0]
      end = self.timeBuffer[-1] + 1./self.samplingFrequency
      bufferElements = self.signalBuffer.reshape(self.channelCount*self.epochSampleCount).tolist()
      self.output[0].append( OVSignalBuffer(start, end, bufferElements) )

   # the process is straightforward
   def process(self):
      if self.channelCount <= 0:
        return
      start = self.timeBuffer[0]
      end = self.timeBuffer[-1]
      if self.getCurrentTime() >= end:
         # deal with data
         self.updateStartTime()
         self.updateEndTime()
         self.updateTimeBuffer()
         self.updateSignalBuffer()
         self.sendSignalBufferToOpenvibe()

   # re-define the uninitialize method to output the end chunk + close streams
   def uninitialize(self):
      if self.channelCount <= 0:
        return
      for inlet in self.inlets:
        inlet.close_stream()
      end = self.timeBuffer[-1]
      self.output[0].append(OVSignalEnd(end, end))
      
      
box = MyOVBox()
