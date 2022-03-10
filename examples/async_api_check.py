import asyncio
import concurrent.futures
import logging

from pupil_labs.realtime_api import Device, StatusUpdateNotifier, receive_gaze_data
from pupil_labs.realtime_api.discovery import Network
from pupil_labs.realtime_api.models import Sensor, Event

from pupil_labs.invisible_lsl_relay import pi_gaze_relay

logger = logging.getLogger(__name__)


async def main():
    discoverer = DeviceDiscoverer(10)
    try:
        await discoverer.get_user_selected_device()
    except TimeoutError:
        logger.error(
            'Make sure your device is connected to the same network.', exc_info=True
        )
    assert discoverer.selected_device_info
    adapter = Adapter(discoverer.selected_device_info)
    await adapter.relay_receiver_to_publisher()
    logger.info('The LSL stream was closed.')


class DeviceDiscoverer:
    def __init__(self, search_timeout):
        self.selected_device_info = None
        self.search_timeout = search_timeout

    async def get_user_selected_device(self):
        async with Network() as network:
            print("Looking for devices in your network...\n\t", end="")
            await network.wait_for_new_device(timeout_seconds=self.search_timeout)

            while self.selected_device_info is None:
                print("\n======================================")
                print("Please select a Pupil Invisible device by index:")
                for device_index, device_name in enumerate(network.devices):
                    print(f"\t{device_index}\t{device_name}")

                print("To reload the list, hit enter.")
                user_input = await input_async()
                self.selected_device_info = evaluate_user_input(
                    user_input, network.devices
                )


class Adapter:
    def __init__(self, selected_device):
        self.receiver = DataReceiver(selected_device)
        self.gaze_publisher = pi_gaze_relay.PupilInvisibleGazeRelay()
        self.event_publisher = pi_gaze_relay.PupilInvisibleEventRelay()
        self.gaze_sample_queue = asyncio.Queue()
        self.publishing_gaze_task = None
        self.publishing_event_task = None
        self.receiving_task = None

    async def receive_gaze_sample(self):
        while True:
            if self.receiver.gaze_sensor_url:
                async for gaze in receive_gaze_data(
                    self.receiver.gaze_sensor_url, run_loop=True, log_level=30
                ):
                    await self.gaze_sample_queue.put(gaze)
            else:
                logger.debug('The gaze sensor was not yet identified.')
                await asyncio.sleep(1)

    async def publish_gaze_sample(self, timeout):
        missing_sample_duration = 0
        while True:
            try:
                sample = await asyncio.wait_for(self.gaze_sample_queue.get(), timeout)
                self.gaze_publisher.push_gaze_sample(sample)
                if missing_sample_duration:
                    missing_sample_duration = 0
            except asyncio.TimeoutError:
                missing_sample_duration += timeout
                logger.warning(
                    'No gaze sample was received for %i seconds.',
                    missing_sample_duration,
                )

    async def publish_event_from_queue(self):
        while True:
            event = await self.receiver.event_queue.get()
            self.event_publisher.push_event_to_outlet(event)

    async def start_receiving_task(self):
        if self.receiving_task:
            logger.debug('Tried to set a new receiving task, but the task is running.')
            return
        self.receiving_task = asyncio.create_task(self.receive_gaze_sample())

    # TODO: start publishing gaze and start publishing event have a very similar
    #  structure - can I merge these functions to one?

    async def start_publishing_gaze(self):
        if self.publishing_gaze_task:
            logger.debug('Tried to set a new gaze publishing task, '
                         'but the task is running.')
            return
        self.publishing_gaze_task = asyncio.create_task(self.publish_gaze_sample(10))

    async def start_publishing_event(self):
        if self.publishing_event_task:
            logger.debug('Tried to set new event publishing task, '
                         'but the task is running.')
            return
        self.publishing_event_task = asyncio.create_task(
            self.publish_event_from_queue())

    async def relay_receiver_to_publisher(self):
        await self.receiver.make_status_update_notifier()
        await self.start_receiving_task()
        await self.start_publishing_gaze()
        await self.start_publishing_event()
        tasks = [self.receiving_task, self.publishing_gaze_task,
                 self.publishing_event_task]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        handle_done_pending_tasks(done, pending)
        await self.receiver.cleanup()


class DataReceiver:
    def __init__(self, device_info):
        self.device_info = device_info
        self.notifier = None
        self.gaze_sensor_url = None
        self.event_queue = asyncio.Queue()
        # self.world_sensor = None

    async def on_update(self, component):
        if isinstance(component, Sensor):
            if component.sensor == 'gaze' and component.conn_type == 'DIRECT':
                self.gaze_sensor_url = component.url
        elif isinstance(component, Event):
            await self.event_queue.put(component)

    async def make_status_update_notifier(self):
        async with Device.from_discovered_device(self.device_info) as device:
            self.notifier = StatusUpdateNotifier(device, callbacks=[self.on_update])
            await self.notifier.receive_updates_start()

    async def cleanup(self):
        await self.notifier.receive_updates_stop()


async def input_async():
    # based on https://gist.github.com/delivrance/675a4295ce7dc70f0ce0b164fcdbd798?permalink_comment_id=3590322#gistcomment-3590322
    with concurrent.futures.ThreadPoolExecutor(1, 'AsyncInput') as executor:
        user_input = await asyncio.get_event_loop().run_in_executor(
            executor, input, '>>> '
        )
        return user_input.strip()


def evaluate_user_input(user_input, device_list):
    try:
        device_info = device_list[int(user_input)]
        return device_info
    except ValueError:
        logger.debug("Reloading the device list.")
        return None
    except IndexError:
        print('Please choose an index from the list!')
        return None


def handle_done_pending_tasks(done, pending):
    for done_task in done:
        try:
            done_task.result()
        except asyncio.CancelledError:
            logger.warning(f"Cancelled: {done_task}")

    for pending_task in pending:
        try:
            pending_task.cancel()
        except asyncio.CancelledError:
            # cancelling is the intended behaviour
            pass


if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(main(), debug=True)
    except KeyboardInterrupt:
        logger.warning("The relay was closed via keyboard interrupt")
