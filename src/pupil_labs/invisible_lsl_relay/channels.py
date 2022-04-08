class PiChannel:
    def __init__(self, sample_query, channel_information_dict):
        self.sample_query = sample_query
        self.information_dict = channel_information_dict

    def append_to(self, channels):
        chan = channels.append_child("channel")
        for entry in self.information_dict:
            chan.append_child_value(entry, self.information_dict[entry])


def pi_event_channels():
    return [
        PiChannel(
            sample_query=pi_extract_from_sample('name'),
            channel_information_dict={'label': "Event", 'format': "string"},
        )
    ]


def pi_gaze_channels():
    channels = []
    # ScreenX, ScreenY: screen coordinates of the gaze cursor
    channels.extend(
        [
            PiChannel(
                sample_query=pi_extract_gaze_query(i),
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


def pi_extract_gaze_query(dim):
    return lambda gaze: [gaze.x, gaze.y][dim]


def pi_extract_from_sample(value):
    return lambda sample: getattr(sample, value)
