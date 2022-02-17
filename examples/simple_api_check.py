from pupil_labs.realtime_api.simple import discover_devices

from pupil_labs.invisible_lsl_relay import pi_gaze_relay


class SimpleDiscovery:
    def __init__(self):
        self.device_list = None
        self.selected_device = None
        self.gaze_stream_running = False

    def get_devices_in_network(self):
        self.device_list = discover_devices(search_duration_seconds=5.0)

    def get_user_selected_device(self):
        if self.device_list is not None:

            while self.selected_device is None:
                print("\n======================================")
                print("Please select a Pupil Invisible device by index:")
                for device_index, device_name in enumerate(self.device_list):
                    print(f"\t{device_index}\t{device_name}")
                print("To reload the list, type 'R'")
                user_input = input(">>> ").strip()
                if user_input.upper() == 'R':
                    print("Reloading the device list.")
                    self.get_devices_in_network()
                    continue
                try:
                    user_input = int(user_input)
                except ValueError:
                    print(
                        f"Your input must be a number between 0 and {len(self.device_list) - 1}"
                    )
                    continue

                # check user input for validity
                if user_input < len(self.device_list):
                    self.selected_device = self.device_list[int(user_input)]
                    print(f"connecting with {self.selected_device}")

    def start_gaze_streaming(self):
        self.gaze_stream_running = True
        try:
            while self.gaze_stream_running:
                yield self.selected_device.receive_gaze_datum()
        except KeyboardInterrupt:
            print("Streaming ended via keyboard input.")
            self.gaze_stream_running = False
        finally:
            print("Stop gaze streaming")
            self.selected_device.close()


def main():
    simple_explorer = SimpleDiscovery()
    simple_explorer.get_devices_in_network()
    simple_explorer.get_user_selected_device()
    print("Start gaze streaming. Exit with ctrl + c")
    relay = pi_gaze_relay.PupilInvisibleGazeRelay()
    gaze_generator = simple_explorer.start_gaze_streaming()
    for gaze in gaze_generator:
        relay.push_gaze_sample(gaze)


if __name__ == '__main__':
    main()
