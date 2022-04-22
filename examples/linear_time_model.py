import numpy as np
from sklearn import linear_model

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
