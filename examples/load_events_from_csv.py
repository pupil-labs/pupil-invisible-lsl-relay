import pandas as pd

path_to_cloud_events = 'cloud_recordings/events.csv'
cloud_events = pd.read_csv(path_to_cloud_events)

cloud_event_names = cloud_events['name']
cloud_event_timestamps = cloud_events['timestamps [ns]']
