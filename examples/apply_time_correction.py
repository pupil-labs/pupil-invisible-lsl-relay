# use convert gaze time stamps from cloud to lsl time
cloud_gaze = pd.read_csv('cloud_recordings/gaze.csv')

# map from nanoseconds to seconds
cloud_gaze['timestamp [s]'] = cloud_gaze['timestamp [ns]'] * 1e-9

# predict lsl time in seconds
cloud_gaze['lsl_time [s]'] = time_mapper.predict(
    cloud_gaze['timestamp [s]'].values.reshape(-1, 1)
)
