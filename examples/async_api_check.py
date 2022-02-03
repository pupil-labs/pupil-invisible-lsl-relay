import asyncio
import concurrent.futures
from pupil_labs.realtime_api import Device, StatusUpdateNotifier, receive_gaze_data
from pupil_labs.realtime_api.models import Sensor
from pupil_labs.realtime_api.discovery import discover_devices
from pupil_labs.invisible_lsl_relay import pi_gaze_relay
import logging

logger = logging.getLogger(__name__)


async def input_async():
    # based on https://gist.github.com/delivrance/675a4295ce7dc70f0ce0b164fcdbd798?permalink_comment_id=3590322#gistcomment-3590322
    with concurrent.futures.ThreadPoolExecutor(1, 'AsyncInput') as executor:
        user_input = await asyncio.get_event_loop().run_in_executor(executor,
                                                                    input,
                                                                    '>>> ')
        return user_input.strip()


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
        # Todo make less complex
        print("Looking for devices in the network...")
        while not self.device_list:
            await self.get_devices_in_network()
            self.n_network_searches += 1

            if self.n_network_searches > 10:
                raise TimeoutError("No device was found in 10 searches.")

        while self.selected_device_info is None:
            print("\n======================================")
            print("Please select a Pupil Invisible device by index:")
            for device_index, device_name in enumerate(self.device_list):
                print(f"\t{device_index}\t{device_name}")

            print("To reload the list, type 'R'")
            user_input = await input_async()

            if user_input.upper() == 'R':
                logger.debug("Reloading the device list.")
                await self.get_devices_in_network()
                continue
            try:
                user_input = int(user_input)
            except ValueError:
                print("Select a device number from the available indices.")
                continue

            # check user input for validity
            if user_input < len(self.device_list):
                logger.debug("valid device selected")
                self.selected_device_info = self.device_list[int(user_input)]


class DataReceiver:

    def __init__(self, device_info):
        self.connected_device = Device.from_discovered_device(device_info)
        logger.debug("connected with %s", self.connected_device)
        self.notifier = None
        self.status = None
        self.gaze_sensor = None
        # self.world_sensor = None
        self.gaze_queue = asyncio.Queue()
        self.stream_task = None

    async def update_status(self):
        self.status = await self.connected_device.get_status()
        self.gaze_sensor = self.status.direct_gaze_sensor()
        # self.world_sensor = self.status.direct_world_sensor()

    async def fetch_gaze(self):
        async for gaze in receive_gaze_data(
            self.gaze_sensor.url, run_loop=True, log_level=30
        ):
            await self.gaze_queue.put(gaze)

    async def start_streaming_task(self):
        if self.stream_task:
            self.stream_task.cancel()
            self.stream_task = None
        self.stream_task = asyncio.create_task(self.fetch_gaze())

    async def on_sensor_connect(self):
        logger.debug('Sensor connected.')
        if not self.stream_task:
            await self.start_streaming_task()
            logger.info("Sensor was connected. Relay will be started.")

    async def on_sensor_disconnect(self):
        logger.warning("Sensor was disconnected.")
        if self.stream_task:
            self.stream_task.cancel()
            self.stream_task = None

    async def check_sensors(self):
        if self.gaze_sensor.connected:
            await self.on_sensor_connect()
        else:
            await self.on_sensor_disconnect()

    async def on_update(self, component):
        if isinstance(component, Sensor):
            if component.sensor == 'gaze' and component.conn_type == 'DIRECT':
                await self.update_status()
                await self.check_sensors()

    async def make_notifier(self):
        self.notifier = StatusUpdateNotifier(self.connected_device,
                                             callbacks=[self.on_update])

    async def start_status_updates(self):
        await self.make_notifier()
        await self.notifier.receive_updates_start()

    async def start_receiving(self):
        await self.update_status()
        await self.start_status_updates()

    async def cleanup(self):
        await self.notifier.receive_updates_stop()
        await self.connected_device.close()
        if self.stream_task:
            self.stream_task.cancel()


class Adapter:
    def __init__(self, selected_device):
        self.receiver = DataReceiver(selected_device)
        self.publisher = pi_gaze_relay.PupilInvisibleGazeRelay()
        self.timeout_check_task = None
        self.receiver_to_publisher_task = None

    async def push_to_publisher(self):
        while True:
            sample = await self.receiver.gaze_queue.get()
            self.publisher.push_gaze_sample(sample)

    async def cleanup(self):
        await self.receiver.cleanup()
        self.receiver_to_publisher_task.cancel()

    async def check_timeout_on_receiver(self, timeout=60):
        empty_time = 0
        while empty_time < timeout:
            if not self.receiver.stream_task:
                logger.warning(f'Gaze sensor stopped streaming. Disconnecting in {timeout-empty_time} seconds')
                empty_time += 1
            else:
                empty_time = 0
            await asyncio.sleep(1)
        await self.cleanup()

    async def relay_receiver_to_publisher(self):
        await self.receiver.start_receiving()

        if self.receiver_to_publisher_task:
            self.receiver_to_publisher_task.cancel()
            self.receiver_to_publisher_task = None
        self.timeout_check_task = asyncio.create_task(self.check_timeout_on_receiver())
        self.receiver_to_publisher_task = asyncio.create_task(self.push_to_publisher())
        try:
            await self.receiver_to_publisher_task
        except asyncio.CancelledError:
            await self.cleanup()
        # todo: handle keyboard interrupt


async def main():
    discoverer = DeviceDiscoverer()
    try:
        await discoverer.get_user_selected_device()
    except TimeoutError:
        logger.error('Make sure your device is connected to the same network.',
                     exc_info=True)
    assert discoverer.selected_device_info
    adapter = Adapter(discoverer.selected_device_info)
    await adapter.relay_receiver_to_publisher()
    logger.info('The LSL stream was closed.')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(), debug=True)

