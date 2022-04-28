# imports for the full pipeline
import numpy as np
from sklearn import linear_model
import pandas as pd
import pyxdf

# import xdf data
# define the name of the stream of interest
stream_name = 'pupil_invisible_Event'

# load xdf data
path_to_recording = './lsl_recordings/recorded_xdf_file.xdf'
data, header = pyxdf.load_xdf(path_to_recording, select_streams=[{'name': stream_name}])

# when recording from one device, there will be only one event stream
# extract this stream from the data
event_stream = data[0]
# extract event names and lsl time stamps
lsl_event_names = np.array(event_stream['time_series']).flatten()
lsl_event_times = np.array(event_stream['time_stamps']).flatten()

# import cloud data
path_to_cloud_events = './cloud_recordings/events.csv'
cloud_events = pd.read_csv(path_to_cloud_events)

# extract and reformat the cloud data to numpy arrays
cloud_event_names = cloud_events['name'].values
cloud_event_timestamps = cloud_events['timestamp [ns]'].values

# filter events that were recorded in the lsl stream and in cloud
name_intersection = np.intersect1d(cloud_event_names, lsl_event_names)

# filter timestamps by the event intersection
filtered_cloud_event_times = np.array(cloud_event_timestamps)[
    np.where(np.isin(cloud_event_names, name_intersection))
]

filtered_lsl_event_times = np.array(lsl_event_times)[
    np.where(np.isin(lsl_event_names, name_intersection))
]

# transform cloud timestamps to seconds
filtered_cloud_event_times = filtered_cloud_event_times * 1e-9

# fit a linear model
time_mapper = linear_model.LinearRegression()
time_mapper.fit(filtered_cloud_event_times.reshape(-1, 1), filtered_lsl_event_times)

# use convert gaze time stamps from cloud to lsl time
cloud_gaze = pd.read_csv('./cloud_recordings/gaze.csv')

# map from nanoseconds to seconds
cloud_gaze['timestamp [s]'] = cloud_gaze['timestamp [ns]'] * 1e-9

# reformat cloud time stamps into a numpy array in correct format
cloud_gaze_timestamps = cloud_gaze['timestamp [s]'].values.reshape(-1, 1)

# predict lsl time in seconds
cloud_gaze['lsl_time [s]'] = time_mapper.predict(cloud_gaze_timestamps)
