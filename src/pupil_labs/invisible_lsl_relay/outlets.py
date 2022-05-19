import logging
import time

import pylsl as lsl

from pupil_labs.invisible_lsl_relay import __version__
from pupil_labs.invisible_lsl_relay.channels import (
    pi_event_channels,
    pi_extract_from_sample,
    pi_gaze_channels,
)

VERSION = __version__

logger = logging.getLogger(__name__)


class PupilInvisibleOutlet:
    def __init__(
        self,
        channel_func,
        outlet_type,
        outlet_format,
        timestamp_query,
        outlet_name_prefix,
        outlet_uuid,
    ):
        self._outlet_uuid = outlet_uuid
        self._channels = channel_func()
        self._outlet = pi_create_outlet(
            self._outlet_uuid,
            self._channels,
            outlet_type,
            outlet_format,
            outlet_name_prefix,
        )
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
    def __init__(self, device_id, outlet_prefix=None):
        PupilInvisibleOutlet.__init__(
            self,
            channel_func=pi_gaze_channels,
            outlet_type='Gaze',
            outlet_format=lsl.cf_double64,
            timestamp_query=pi_extract_from_sample('timestamp_unix_seconds'),
            outlet_name_prefix=outlet_prefix,
            outlet_uuid=f'{device_id}_Gaze',
        )


class PupilInvisibleEventOutlet(PupilInvisibleOutlet):
    def __init__(self, device_id, outlet_prefix=None):
        PupilInvisibleOutlet.__init__(
            self,
            channel_func=pi_event_channels,
            outlet_type='Event',
            outlet_format=lsl.cf_string,
            timestamp_query=pi_extract_from_sample('timestamp_unix_seconds'),
            outlet_name_prefix=outlet_prefix,
            outlet_uuid=f'{device_id}_Event',
        )


def pi_create_outlet(
    outlet_uuid, channels, outlet_type, outlet_format, outlet_name_prefix
):
    stream_info = pi_streaminfo(
        outlet_uuid, channels, outlet_type, outlet_format, outlet_name_prefix
    )
    return lsl.StreamOutlet(stream_info)


def pi_streaminfo(
    outlet_uuid, channels, type_name: str, channel_format, outlet_name_prefix
):
    stream_info = lsl.StreamInfo(
        name=f"{outlet_name_prefix}_{type_name}",
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
