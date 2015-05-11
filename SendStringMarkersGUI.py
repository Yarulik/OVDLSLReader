 
import sys; sys.path.append('./lib') # help python find pylsl relative to this example program
from pylsl import StreamInfo, StreamOutlet

from Tkinter import *


# Stream info
info = StreamInfo('XpTiming','Markers',1,0,'string','myuixp1337');

# next make an outlet
outlet = StreamOutlet(info)

print("now sending markers...")

# List of used markers -- see "lua-stimulator-stim-codes.lua" for a complete list.
markernames = ['OVTK_GDF_Start_Of_Trial', 'OVTK_StimulationId_Label_01', 'OVTK_StimulationId_Label_02', 'OVTK_GDF_End_Of_Trial']

buttons = []
last_but = 0

def send(but_num):
  global last_but
  mark = markernames[but_num]
  print "Sending: ", mark
  outlet.push_sample([mark])
  # feedback: change button color
  (buttons[last_but]).config(bg='white')
  (buttons[last_but]).config(activebackground='red')
  (buttons[but_num]).config(bg='green')
  (buttons[but_num]).config(activebackground='green')
  last_but = but_num
  master.update()

master = Tk()
master.wm_title("LSL stim")



# create buttons
for i in range(len(markernames)):
  # associate callback, using lambda for parameters
  b = Button(master, text=markernames[i], command=lambda num=i: send(num))
  b.config(bg='white')
  b.config(activebackground='red')
  b.pack(padx=5, pady=5)
  buttons.append(b)
 
mainloop()
