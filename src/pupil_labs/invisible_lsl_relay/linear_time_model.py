# imports for the full pipeline
import logging
import pathlib
from collections import namedtuple

import numpy as np
import pandas as pd
import pyxdf
from sklearn import linear_model

logger = logging.getLogger(__name__)

event_column_name = 'name'
event_column_timestamp = 'timestamp [s]'


def perform_time_alignment(xdf_path, cloud_path, xdf_serial_num):
    """
    :param xdf_path: pathlib path pointing to the xdf file with all data streams
    :param cloud_path: pathlib path pointing to the directory with all cloud recordings
    :param xdf_serial_num: string specifying the serial number to look for in the xdf file
    :return:
    cloud_aligned_time - pandas data frame from cloud_path/gaze.csv with an
    additional column for the mapped lsl time
    time_mapper - linear regression model mapping time from xdf to cloud
    """
    logger.debug(f'performing time alignment between {xdf_path} and {cloud_path}')

    filtered_xdf_data, filtered_cloud_data = get_filtered_events(
        xdf_path, cloud_path, xdf_serial_num
    )

    result = fit_linear_model(
        filtered_xdf_data, filtered_cloud_data, cloud_path
    )
    return result


def get_filtered_events(xdf_path, cloud_path, xdf_serial_num):
    xdf_event_data = load_xdf_events(xdf_path, world_camera_serial_num=xdf_serial_num)
    cloud_event_data = load_cloud_data(cloud_path)

    filtered_cloud_data, filtered_xdf_data = filter_common_events(
        xdf_event_data, cloud_event_data
    )

    return filtered_cloud_data, filtered_xdf_data


def load_xdf_events(path_to_xdf_recording, world_camera_serial_num):
    stream_type = 'Event'
    data, header = pyxdf.load_xdf(
        path_to_xdf_recording, select_streams=[{'type': stream_type}]
    )

    # need to extract event screen with the correct scene camera
    for event_stream in data:
        if (
            event_stream['info']['desc'][0]['acquisition'][0]['world_camera_serial'][0]
            == world_camera_serial_num
        ):
            return xdf_event_to_df(event_stream)
    raise ValueError(
        f'None of streams in {path_to_xdf_recording} contained '
        f'the serial number {world_camera_serial_num}!'
    )


def xdf_event_to_df(
    event_stream, column_name=event_column_name, column_timestamp=event_column_timestamp
):
    lsl_event_data = pd.DataFrame(
        {
            column_name: [name[0] for name in event_stream['time_series']]
            column_timestamp: event_stream['time_stamps']
        }
    )

    return lsl_event_data


def load_cloud_data(cloud_path, column_timestamp=event_column_timestamp):
    cloud_event_data = load_df_from_dir(cloud_path, 'events.csv')
    # transform cloud timestamps to seconds
    cloud_event_data[column_timestamp] = cloud_event_data['timestamp [ns]'] * 1e-9

    return cloud_event_data


def filter_common_events(cloud_data, xdf_data, column_name=event_column_name):

    name_intersection = np.intersect1d(cloud_data[column_name], xdf_data[column_name])

    # filter timestamps by the event intersection
    filtered_cloud_data = cloud_data[cloud_data[column_name].isin(name_intersection)]
    filtered_xdf_data = xdf_data[xdf_data[column_name].isin(name_intersection)]

    return filtered_cloud_data, filtered_xdf_data


def fit_linear_model(
    filtered_cloud_data,
    filtered_xdf_data,
    cloud_path,
    file_name='gaze.csv',
    column_timestamp=event_column_timestamp,
):

    cloud_to_lsl_mapper = linear_time_mapper(
        filtered_cloud_data[[column_timestamp]], filtered_xdf_data[column_timestamp]
    )
    lsl_to_cloud_mapper = linear_time_mapper(
        filtered_xdf_data[[column_timestamp]], filtered_cloud_data[column_timestamp]
    )
    # load the file with the gaze data
    cloud_gaze_data = load_df_from_dir(cloud_path, file_name)
    # map from nanoseconds to seconds
    cloud_gaze_data[column_timestamp] = cloud_gaze_data['timestamp [ns]'] * 1e-9

    # map cloud time to lsl time in seconds
    cloud_gaze_data['lsl_time [s]'] = cloud_to_lsl_mapper.predict(
        cloud_gaze_data[[column_timestamp]]
    )

    Result = namedtuple('Result',
                        ['cloud_aligned_time', 'cloud_to_lsl', 'lsl_to_cloud'])
    return Result(cloud_gaze_data, cloud_to_lsl_mapper, lsl_to_cloud_mapper)


def linear_time_mapper(x, y):
    mapper = linear_model.LinearRegression()
    mapper.fit(x, y)

    return mapper


def load_df_from_dir(dir_name, file_name):
    files = list(pathlib.Path(dir_name).rglob(file_name))
    if len(files) != 1:
        raise ValueError(
            f'There was not the correct number of event files in the '
            f"directory {dir_name} and it's sub directories."
            f'expected one file, but got {len(file_name)}.'
        )

    return pd.read_csv(files[0])
