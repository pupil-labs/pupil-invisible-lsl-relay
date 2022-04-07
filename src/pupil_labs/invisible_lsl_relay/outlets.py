import logging
import time
import uuid

import pylsl as lsl
from pupil_labs.invisible_lsl_relay.channels import pi_extract_from_sample, \
    pi_gaze_channels, pi_event_channels


VERSION = "1.0"

logger = logging.getLogger(__name__)


class PupilInvisibleOutlet:
    def __init__(self, channel_func, outlet_name, outlet_format, timestamp_query,
                 outlet_uuid):
        self._outlet_uuid = outlet_uuid
        self._channels = channel_func()
        self._outlet = pi_create_outlet(self._outlet_uuid, self._channels, outlet_name,
                                        outlet_format)
        self._timestamp_query = timestamp_query

    def push_sample_to_outlet(self, sample):
        try:
            sample_to_push = [chan.sample_query(sample) for chan in self._channels]
            timestamp_to_push = self._timestamp_query(sample) - get_lsl_time_offset()
        except Exception as exc:
            logger.error(f"Error extracting from sample: {exc}")
            logger.debug(str(sample))
            return
        self._outlet.push_sample(sample_to_push, timestamp_to_push)


class PupilInvisibleGazeOutlet(PupilInvisibleOutlet):
    def __init__(self, device_id=None):
        PupilInvisibleOutlet.__init__(self,
                                      channel_func=pi_gaze_channels,
                                      outlet_name='Gaze',
                                      outlet_format=lsl.cf_double64,
                                      timestamp_query=pi_extract_from_sample(
                                          'timestamp_unix_seconds'),
                                      outlet_uuid=f'{device_id or str(uuid.uuid4())}_Gaze')


class PupilInvisibleEventOutlet(PupilInvisibleOutlet):
    def __init__(self, device_id=None):
        PupilInvisibleOutlet.__init__(self,
                                      channel_func=pi_event_channels,
                                      outlet_name='Event',
                                      outlet_format=lsl.cf_string,
                                      timestamp_query=pi_extract_from_sample(
                                          'timestamp_unix_seconds'),
                                      outlet_uuid=f'{device_id or str(uuid.uuid4())}_Event')


def pi_create_outlet(outlet_uuid, channels, outlet_name, outlet_format):
    stream_info = pi_streaminfo(outlet_uuid, channels, outlet_name,
                                outlet_format)
    return lsl.StreamOutlet(stream_info)


def pi_streaminfo(outlet_uuid, channels, type_name: str, channel_format):
    stream_info = lsl.StreamInfo(
        name=f"pupil_invisible_{type_name}",
        type=type_name,
        channel_count=len(channels),
        channel_format=channel_format,
        source_id=outlet_uuid,
    )
    stream_info.desc().append_child_value("pupil_invisible_lsl_relay_version", VERSION)
    xml_channels = stream_info.desc().append_child("channels")
    [chan.append_to(xml_channels) for chan in channels]
    return stream_info


def get_lsl_time_offset():
    return time.time() - lsl.local_clock()
