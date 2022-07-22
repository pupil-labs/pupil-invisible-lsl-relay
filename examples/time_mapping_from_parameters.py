# imports for the full pipeline
import json
import pandas as pd

column_timestamp = 'timestamp [s]'

# use convert gaze time stamps from cloud to lsl time
cloud_gaze_data = pd.read_csv('./recordings/gaze.csv')

# map from nanoseconds to seconds
cloud_gaze_data[column_timestamp] = cloud_gaze_data['timestamp [ns]'] * 1e-9

# import the parameter dictionary
with open('./recordings/time_alignment_parameters.json') as file:
    parameter_dict = json.load(file)


def perform_linear_mapping(input_data, parameters):
    return parameters['intercept'] + input_data * parameters['slope']


# predict lsl time in seconds
cloud_gaze_data['lsl_time [s]'] = perform_linear_mapping(
    cloud_gaze_data[column_timestamp],
    parameter_dict['cloud_to_lsl'])

cloud_gaze_data.to_csv('./recordings/time_aligned_gaze.csv')
