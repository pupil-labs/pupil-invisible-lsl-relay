import asyncio
import concurrent.futures
from pupil_labs.realtime_api import Device, StatusUpdateNotifier, receive_gaze_data
from pupil_labs.realtime_api.models import Sensor
from pupil_labs.realtime_api.discovery import discover_devices
from pupil_labs.invisible_lsl_relay import pi_gaze_relay
import logging


class DeviceDiscoverer:
    def __init__(self):
        self.device_list = None
        self.selected_device_info = None
        self.search_timeout = 10
        self.n_network_searches = 0

    async def get_devices_in_network(self):
        device_discoverer = discover_devices(timeout_seconds=self.search_timeout)
        self.device_list = [device async for device in device_discoverer]

    async def get_user_selected_device(self):
        while not self.device_list:
            print('Looking for devices in the network...')
            await self.get_devices_in_network()
            self.n_network_searches += 1

            if self.n_network_searches > 10:
                raise TimeoutError('No device was found in 10 searches.')

        while self.selected_device_info is None:
            print("\n======================================")
            print("Please select a Pupil Invisible device by index:")
            for device_index, device_name in enumerate(self.device_list):
                print(f"\t{device_index}\t{device_name}")

            print("To reload the list, type 'R'")
            with concurrent.futures.ThreadPoolExecutor(1, 'AsyncInput') as executor:
                user_input = await asyncio.get_event_loop().run_in_executor(executor,
                                                                            input,
                                                                            '>>> ')
                user_input = user_input.strip()

            if user_input.upper() == 'R':
                print("Reloading the device list.")
                await self.get_devices_in_network()
                continue
            try:
                user_input = int(user_input)
            except ValueError:
                print(f"Select a device number from the available indices.")
                continue

            # check user input for validity
            if user_input < len(self.device_list):
                print('valid device selected')
                self.selected_device_info = self.device_list[int(user_input)]


class DeviceConnector:

    def __init__(self, device_info):
        self.connected_device = Device.from_discovered_device(device_info)
        print(f"connected with {self.connected_device}")
        self.notifier = None
        self.status = None
        self.gaze_sensor = None
        # self.world_sensor = None
        self.gaze_queue = asyncio.Queue()
        self.stream_task = None
        self.relay_task = None
        self.cleanup_task = None

    async def update_status(self):
        self.status = await self.connected_device.get_status()
        self.gaze_sensor = self.status.direct_gaze_sensor()
        # self.world_sensor = self.status.direct_world_sensor()

    async def fetch_gaze(self):
        async for gaze in receive_gaze_data(
            self.gaze_sensor.url, run_loop=True
        ):
            await self.gaze_queue.put(gaze)

    async def start_streaming_task(self):
        self.stream_task = asyncio.create_task(self.fetch_gaze())

    async def on_sensor_connect(self):
        if not self.stream_task:
            await self.start_streaming_task()
        if self.cleanup_task:
            self.cleanup_task.cancel()
            print(self.cleanup_task)
            self.cleanup_task = None
            print('Sensor was reconnected. Relay will continue.')

    async def cleanup(self):
        await self.notifier.receive_updates_stop()
        await self.connected_device.close()
        if self.stream_task:
            self.stream_task.cancel()
        if self.relay_task:
            self.relay_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()

    async def cleanup_after_timeout(self):
        print('Sensor not connected. Relay will close in 60 seconds.')
        await asyncio.sleep(60)
        await self.cleanup()

    async def on_sensor_disconnect(self):
        if self.stream_task:
            self.stream_task.cancel()
            print(self.stream_task)
            self.stream_task = None
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self.cleanup_after_timeout())

    async def check_sensors(self):
        if self.gaze_sensor.connected:
            await self.on_sensor_connect()
        else:
            await self.on_sensor_disconnect()

    async def on_update(self, component):
        print(component)
        if isinstance(component, Sensor):
            if component.sensor == 'gaze' and component.conn_type == 'DIRECT':
                await self.update_status()
                await self.check_sensors()

    async def make_notifier(self):
        self.notifier = StatusUpdateNotifier(self.connected_device,
                                             callbacks=[self.on_update])

    async def start_status_updates(self):
        await self.update_status()
        await self.make_notifier()
        await self.notifier.receive_updates_start()


async def start_relaying_task(connector, relay):
    async def _push_to_relay():
        while True:
            sample = await connector.gaze_queue.get()
            relay.push_gaze_sample(sample)

    connector.relay_task = asyncio.create_task(_push_to_relay())


async def main():
    discoverer = DeviceDiscoverer()
    try:
        await discoverer.get_user_selected_device()
    except TimeoutError:
        print('Make sure your device is connected to the same network.')
    assert discoverer.selected_device_info
    connection = DeviceConnector(discoverer.selected_device_info)

    try:
        await connection.start_status_updates()

        relay = pi_gaze_relay.PupilInvisibleGazeRelay()
        await start_relaying_task(connection, relay)

        while not (connection.stream_task and connection.relay_task):
            await asyncio.sleep(0.1)

        await asyncio.gather(*[connection.stream_task, connection.relay_task],
                             return_exceptions=True)

    except KeyboardInterrupt:
        pass
    finally:
        if not connection.cleanup_task:
            await connection.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main(), debug=True)
