 

Tested with OpenViBE 1.0 and linux 64 (kubuntu 14.04).

May not work with other system without modifying "pylsl.py" and "libname" variable according to openvibe naming convention.

* python_lsl.py: openvibe script to read data
* test_python_lsl.xml: corresponding openvibe scenario to test it

* SendStringMarkers.py: generate random LSL stimulations
* SendStringMarkersGUI.py: same, with a nice GUI and a mouse
* python_lsl_stims.py: openvibe script to read stimulations
* test_python_lsl_stim_reader.xml: corresponding openvibe scenario to test it

# bluff_game branch

GUI aimed at "bluff game" project.

* OVTK_StimulationId_ExperimentStart / OVTK_StimulationId_ExperimentStop: obviously, very beginning and end of the whole experiment
* OVTK_StimulationId_BaselineStart / OVTK_StimulationId_BaselineStop: part where rules are explained
* OVTK_StimulationId_SegmentStart / OVTK_StimulationId_SegmentStop: start / stop of a session of one of the heart feedback modality (stop before questionnaires)
* OVTK_StimulationId_TrialStart / OVTK_StimulationId_TrialStop: start / stop of a play

Also new scenario, which records LSL streams involved: bluff_game_record.xml

