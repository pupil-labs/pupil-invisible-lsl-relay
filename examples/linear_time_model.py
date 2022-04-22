import pyxdf
import numpy as np
import pandas as pd
from sklearn import linear_model

# import xdf and cloud data

# xdf data
stream_name = 'pupil_invisible_Event'
path_to_recording = './lsl_recordings/recorded_xdf_file.xdf'
data, header = pyxdf.load_xdf(path_to_recording)

is_event_stream = [stream_name in stream['info']['name'] for stream in data]
event_stream = np.array(data)[np.where(is_event_stream)][0]

lsl_event_names = event_stream['times series']
lsl_event_times = event_stream['time stamps']

# cloud data
path_to_cloud_events = 'cloud_recordings/events.csv'
cloud_events = pd.read_csv(path_to_cloud_events)

cloud_event_names = cloud_events['name']
cloud_event_timestamps = cloud_events['timestamps [ns]']


# filter events that were recorded in the lsl stream and in cloud
name_intersection = np.intersect1d(cloud_event_names, lsl_event_names)

# filter timestamps by the event intersection
filtered_cloud_event_times = np.array(cloud_event_timestamps)[np.where(
    cloud_event_names.isin(name_intersection))]

filtered_lsl_event_times = np.array(lsl_event_times)[np.where(
    np.isin(np.array(lsl_event_names).flatten(), name_intersection)
)]

# transform cloud timestamps to seconds
filtered_cloud_event_times = filtered_cloud_event_times * 1e-9

# fit a linear model
time_mapper = linear_model.LinearRegression()
time_mapper.fit(filtered_cloud_event_times.reshape(-1, 1), filtered_lsl_event_times)

# use convert gaze time stamps from cloud to lsl time
cloud_gaze = pd.read_csv('cloud_recordings/gaze.csv')

# map from nanoseconds to seconds
cloud_gaze['timestamp [s]'] = cloud_gaze['timestamp [ns]'] * 1e-9

# predict lsl time in seconds
cloud_gaze['lsl_time [s]'] = time_mapper.predict(
    cloud_gaze['timestamp [s]'].values.reshape(-1, 1))

