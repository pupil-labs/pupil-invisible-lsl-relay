import logging
import time
import uuid

import pylsl as lsl

VERSION = "1.0"


logger = logging.getLogger(__name__)


class PupilInvisibleRelay:
    def __init__(self, channel_func, outlet_func, outlet_uuid=None):
        self._time_offset = time.time() - lsl.local_clock()
        self._outlet_uuid = outlet_uuid or str(uuid.uuid4())
        self._channels = channel_func()
        self._outlet = outlet_func(self._outlet_uuid, self._channels)


class PupilInvisibleGazeRelay(PupilInvisibleRelay):
    def __init__(self, outlet_uuid=None):
        PupilInvisibleRelay.__init__(
            self, pi_gaze_channels, pi_gaze_outlet, outlet_uuid
        )

    def push_gaze_sample(self, gaze):
        try:
            sample = [chan.query(gaze) for chan in self._channels]
            timestamp = gaze.timestamp_unix_seconds - self._time_offset
        except Exception as exc:
            logger.error(f"Error extracting gaze sample: {exc}")
            logger.debug(str(gaze))
            return
        # push_chunk might be more efficient but does not
        # allow setting explicit timestamps for all samples
        self._outlet.push_sample(sample, timestamp)


class PupilInvisibleEventRelay(PupilInvisibleRelay):
    def __init__(self, outlet_uuid=None):
        PupilInvisibleRelay.__init__(
            self, pi_event_channels, pi_event_outlet, outlet_uuid
        )

    def push_event_to_outlet(self, event):
        event_name = [chan.query(event) for chan in self._channels]
        timestamp = event.timestamp - self._time_offset
        self._outlet.push_sample(event_name, timestamp)


def pi_gaze_outlet(outlet_uuid, channels):
    stream_info = pi_streaminfo(outlet_uuid, channels, "Gaze", lsl.cf_double64)
    return lsl.StreamOutlet(stream_info)


def pi_event_outlet(outlet_uuid, channels):
    stream_info = pi_streaminfo(outlet_uuid, channels, 'Event', 'string')
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
    return [EventChannel(pi_event_name_query, "Event", "string")]


def pi_gaze_channels():
    channels = []

    # ScreenX, ScreenY: screen coordinates of the gaze cursor
    channels.extend(
        [
            GazeChannel(
                query=pi_extract_screen_query(i),
                label="xy"[i],
                eye="both",
                metatype="Screen" + "XY"[i],
                unit="pixels",
                coordinate_system="world",
            )
            for i in range(2)
        ]
    )

    # PupilInvisibleTimestamp: original Pupil Invisible UNIX timestamp
    channels.extend(
        [
            GazeChannel(
                query=pi_extract_timestamp_query(),
                label="pi_timestamp",
                eye="both",
                metatype="PupilInvisibleTimestamp",
                unit="seconds",
            )
        ]
    )
    return channels


def pi_extract_screen_query(dim):
    return lambda gaze: [gaze.x, gaze.y][dim]


def pi_extract_timestamp_query():
    return lambda gaze: gaze.timestamp_unix_seconds


def pi_event_name_query(event):
    return event.name


class GazeChannel:
    def __init__(self, query, label, eye, metatype, unit, coordinate_system=None):
        self.label = label
        self.eye = eye
        self.metatype = metatype
        self.unit = unit
        self.coordinate_system = coordinate_system
        self.query = query

    def append_to(self, channels):
        chan = channels.append_child("channel")
        chan.append_child_value("label", self.label)
        chan.append_child_value("eye", self.eye)
        chan.append_child_value("type", self.metatype)
        chan.append_child_value("unit", self.unit)
        if self.coordinate_system:
            chan.append_child_value("coordinate_system", self.coordinate_system)


class EventChannel:
    def __init__(self, query, label, unit):
        self.query = query
        self.label = label
        self.unit = unit

    def append_to(self, channels):
        chan = channels.append_child("channel")
        chan.append_child_value("label", self.label)
        chan.append_child_value("unit", self.unit)
