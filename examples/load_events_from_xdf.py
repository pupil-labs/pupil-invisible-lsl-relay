import numpy as np
import pyxdf

# define the name of the stream of interest
stream_name = 'pupil_invisible_Event'

# load xdf data
path_to_recording = './lsl_recordings/recorded_xdf_file.xdf'
data, header = pyxdf.load_xdf(path_to_recording)

# make a list of streams with matching names
is_event_stream = [stream_name in stream['info']['name'] for stream in data]

# filter event stream
event_stream = np.array(data)[np.where(is_event_stream)][0]

lsl_event_names = event_stream['times series']
lsl_event_times = event_stream['time stamps']
