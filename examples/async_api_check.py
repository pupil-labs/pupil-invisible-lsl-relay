import asyncio
from pupil_labs.realtime_api import Device, StatusUpdateNotifier, receive_gaze_data
from pupil_labs.realtime_api.discovery import discover_devices
import importlib.util
spec = importlib.util.spec_from_file_location("module.name",
                                              "../src/pupil_labs/invisible_lsl_relay/pi_gaze_relay.py")
pi_gaze_relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pi_gaze_relay)
# from pupil_labs.invisible_lsl_relay import pi_gaze_relay
# the above implementation doesn't work, presumably, because the pupil_labs folder
# in the interpreter directory masks the pupil_labs directory in src


class DeviceDiscoverer:
    def __init__(self):
        self.device_list = None
        self.selected_device_info = None

    async def get_devices_in_network(self):
        device_discoverer = discover_devices(timeout_seconds=5)
        self.device_list = [device async for device in device_discoverer]

    async def get_user_selected_device(self):
        while self.device_list is None:
            print('Looking for devices in the network...')
            await self.get_devices_in_network()

        while self.selected_device_info is None:
            print("\n======================================")
            print("Please select a Pupil Invisible device by index:")
            for device_index, device_name in enumerate(self.device_list):
                print(f"\t{device_index}\t{device_name}")

            print("To reload the list, type 'R'")
            user_input = input(">>> ").strip()
            if user_input.upper() == 'R':
                print("Reloading the device list.")
                await self.get_devices_in_network()
                continue
            try:
                user_input = int(user_input)
            except ValueError:
                print(f"Your input must be a number between 0 and {len(self.device_list)-1}")
                continue

            # check user input for validity
            if user_input < len(self.device_list):
                print('valid device selected')
                self.selected_device_info = self.device_list[int(user_input)]


async def on_update(component):
    print(f"One component has changed: {component}")
    # Todo: Filter for event updates


class DeviceConnector:
    def __init__(self, device_info):
        self.connected_device = Device.from_discovered_device(device_info)
        print(f"connected with {self.connected_device}")
        self.status = None
        self.gaze = None
        self.world = None
        self.notifier = StatusUpdateNotifier(self.connected_device,
                                             callbacks=[on_update])
        self.is_streaming = False

    async def setup(self):
        self.status = await self.connected_device.get_status()
        self.gaze = self.status.direct_gaze_sensor()
        self.world = self.status.direct_world_sensor()

    async def fetch_gaze(self):
        async for gaze in receive_gaze_data(
            self.gaze.url, run_loop=True
        ):
            yield gaze

    async def start_status_updates(self):
        print("Starting auto-update")
        await self.notifier.receive_updates_start()

    async def close(self):
        print("Stopping auto-update")
        await self.notifier.receive_updates_stop()
        # Todo: close client section
        # Todo: close connection


async def gaze_data_relay(connection, relay):
    connection.is_streaming = True
    try:
        while True:
            print("Start gaze streaming")
            gaze_generator = connection.fetch_gaze()
            async for gaze in gaze_generator:
                relay.push_gaze_sample(gaze)
    except KeyboardInterrupt:
        pass
    finally:
        await connection.close()


async def main():
    discoverer = DeviceDiscoverer()
    await discoverer.get_user_selected_device()
    connection = DeviceConnector(discoverer.selected_device_info)
    await connection.setup()
    await connection.start_status_updates()
    relay = pi_gaze_relay.PupilInvisibleGazeRelay()
    try:
        await gaze_data_relay(connection, relay)
    except KeyboardInterrupt:
        pass
    finally:
        print("Closing gaze relay.")

if __name__ == "__main__":
    asyncio.run(main())

