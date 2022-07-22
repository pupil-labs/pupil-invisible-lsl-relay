:tocdepth: 3

************************************************************
Preforming accurate time synchronization between two devices
************************************************************
You can use lsl to synchronize two Pupil Invisible Devices.


Description of the Choreography
===============================
We placed two Pupil Invisible Glasses in front of a light source, the eye cameras facing towards the light.
The scene cameras were detached from the glasses and the light source was switched off during setup. The Companion
Devices were set up such that both would upload the recorded data to the same Workspace.

An lsl relay was started for each of the Pupil Invisible Glasses, and the two lsl Event streams were recorded with
the LabRecorder. We did not record the lsl Gaze streams for this example.

After the lsl streams were running and being recording by the LabRecorder, we started recording in the Pupil Invisible
Companion App. After this step, the following data series were being recorded:

- Event data from each of the two Pupil Invisible Glasses (two data streams) are streamed and recorded via lsl and
  the LabRecorder.
- Event data from each pair of Pupil Invisible Glasses is saved locally on the Companion Device during the recording
  and uploaded to cloud once the recording completed.
- Eye Camera Images from each pair of Pupil Invisible Glasses are saved locally on the Companion Device and uploaded
  to Pupil Cloud when the recording completed. The 200 Hz Gaze position estimate is computed in Pupil Cloud.

With this setup in place and all recordings running, we switched the light source pointing at the eye cameras on
and off four times. This created a simultaneous signal recorded by the Eye Cameras (brightness increases).

After that, we stopped all recordings in the inverse order (first in the companion app, then in the LabRecorder) and
stopped the lsl relay.


