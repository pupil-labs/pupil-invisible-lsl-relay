import logging
import time
import uuid

import pylsl as lsl

VERSION = "1.0"


logger = logging.getLogger(__name__)


class PupilInvisibleRelay:
    def __init__(
        self,
        channel_func,
        outlet_name,
        outlet_format,
        timestamp_query,
        outlet_uuid=None,
    ):
        self._time_offset = time.time() - lsl.local_clock()
        self._outlet_uuid = outlet_uuid or str(uuid.uuid4())
        self._channels = channel_func()
        self._outlet = pi_create_outlet(
            self._outlet_uuid, self._channels, outlet_name, outlet_format
        )
        self._timestamp_query = timestamp_query

    def push_sample_to_outlet(self, sample):
        try:
            sample_to_push = [chan.sample_query(sample) for chan in self._channels]
            timestamp_to_push = self._timestamp_query(sample) - self._time_offset
        except Exception as exc:
            logger.error(f"Error extracting from sample: {exc}")
            logger.debug(str(sample))
            return
        self._outlet.push_sample(sample_to_push, timestamp_to_push)


class PupilInvisibleGazeRelay(PupilInvisibleRelay):
    def __init__(self, outlet_uuid=None):
        PupilInvisibleRelay.__init__(
            self,
            channel_func=pi_gaze_channels,
            outlet_name='Gaze',
            outlet_format=lsl.cf_double64,
            timestamp_query=pi_extract_from_sample('timestamp_unix_seconds'),
            outlet_uuid=outlet_uuid,
        )


class PupilInvisibleEventRelay(PupilInvisibleRelay):
    def __init__(self, outlet_uuid=None):
        PupilInvisibleRelay.__init__(
            self,
            channel_func=pi_event_channels,
            outlet_name='Event',
            outlet_format=lsl.cf_string,
            timestamp_query=pi_extract_from_sample('timestamp_unix_seconds'),
            outlet_uuid=outlet_uuid,
        )


class PupilInvisibleTimestampRelay(PupilInvisibleRelay):
    def __init__(self, outlet_uuid=None):
        PupilInvisibleRelay.__init__(
            self,
            channel_func=pi_timestamp_channels,
            outlet_name='Timestamp',
            outlet_format=lsl.cf_float32,
            timestamp_query=pi_extract_from_sample('timestamp_unix_seconds'),
            outlet_uuid=outlet_uuid,
        )


def pi_create_outlet(outlet_uuid, channels, outlet_name, outlet_format):
    stream_info = pi_streaminfo(outlet_uuid, channels, outlet_name, outlet_format)
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


def pi_event_channels():
    return [
        PiChannel(
            sample_query=pi_extract_from_sample('name'),
            channel_information_dict={'label': "Event", 'format': "string"},
        )
    ]


def pi_timestamp_channels():
    return [
        PiChannel(
            sample_query=pi_extract_from_sample('timestamp_unix_ns'),
            channel_information_dict={'label': 'Timestamp', 'unit': 'nanoseconds'},
        )
    ]


def pi_gaze_channels():
    channels = []

    # ScreenX, ScreenY: screen coordinates of the gaze cursor
    channels.extend(
        [
            PiChannel(
                sample_query=pi_extract_screen_query(i),
                channel_information_dict={
                    'label': "xy"[i],
                    'eye': "both",
                    'metatype': "Screen" + "XY"[i],
                    'unit': "pixels",
                    'coordinate_system': "world",
                },
            )
            for i in range(2)
        ]
    )
    return channels


def pi_extract_screen_query(dim):
    return lambda gaze: [gaze.x, gaze.y][dim]


def pi_extract_from_sample(value):
    return lambda sample: getattr(sample, value)


class PiChannel:
    def __init__(self, sample_query, channel_information_dict):
        self.sample_query = sample_query
        self.information_dict = channel_information_dict

    def append_to(self, channels):
        chan = channels.append_child("channel")
        for entry in self.information_dict:
            chan.append_child_value(entry, self.information_dict[entry])
