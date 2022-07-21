import pandas as pd

from pupil_labs.invisible_lsl_relay.linear_time_model import TimeAlignmentModels

event_column_name = 'name'
event_column_timestamp = 'timestamp [s]'

models = TimeAlignmentModels.read_json(
    "./cloud_recordings/time_alignment_parameters.json"
)

# use convert gaze time stamps from cloud to lsl time
cloud_gaze_data = pd.read_csv('./cloud_recordings/gaze.csv')

# map from nanoseconds to seconds
cloud_gaze_data[event_column_timestamp] = cloud_gaze_data['timestamp [ns]'] * 1e-9

# predict lsl time in seconds
cloud_gaze_data['lsl_time [s]'] = models.cloud_to_lsl.predict(
    cloud_gaze_data[[event_column_timestamp]].values
)
