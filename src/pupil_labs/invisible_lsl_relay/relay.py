import asyncio
import logging

from pupil_labs.realtime_api import Device, StatusUpdateNotifier, receive_gaze_data
from pupil_labs.realtime_api.models import Event, Sensor

from pupil_labs.invisible_lsl_relay import outlets

logger = logging.getLogger(__name__)


class Relay:
    def __init__(self, selected_device):
        self.device_info = selected_device
        self.receiver = DataReceiver(selected_device)
        self.gaze_outlet = outlets.PupilInvisibleGazeOutlet(selected_device.name)
        self.event_outlet = outlets.PupilInvisibleEventOutlet(selected_device.name)
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
                self.gaze_outlet.push_sample_to_outlet(sample)
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
            self.event_outlet.push_sample_to_outlet(event)

    async def start_receiving_task(self):
        if self.receiving_task:
            logger.debug('Tried to set a new receiving task, but the task is running.')
            return
        self.receiving_task = asyncio.create_task(self.receive_gaze_sample())

    async def start_publishing_gaze(self):
        if self.publishing_gaze_task:
            logger.debug(
                'Tried to set a new gaze publishing task, but the task is running.'
            )
            return
        self.publishing_gaze_task = asyncio.create_task(self.publish_gaze_sample(10))

    async def start_publishing_event(self):
        if self.publishing_event_task:
            logger.debug(
                'Tried to set new event publishing task, but the task is running.'
            )
            return
        self.publishing_event_task = asyncio.create_task(
            self.publish_event_from_queue()
        )

    async def relay_receiver_to_publisher(self, time_sync_interval):
        await self.receiver.make_status_update_notifier()
        await self.start_receiving_task()
        await self.start_publishing_gaze()
        await self.start_publishing_event()
        tasks = [
            self.receiving_task,
            self.publishing_gaze_task,
            self.publishing_event_task,
        ]
        # start time sync task
        if time_sync_interval:
            time_sync_task = asyncio.create_task(
                send_events_in_interval(self.device_info, time_sync_interval)
            )
            tasks.append(time_sync_task)

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        handle_done_pending_tasks(done, pending)
        await self.receiver.cleanup()


class DataReceiver:
    def __init__(self, device_info):
        self.device_info = device_info
        self.notifier = None
        self.gaze_sensor_url = None
        self.event_queue = asyncio.Queue()

    async def on_update(self, component):
        if isinstance(component, Sensor):
            if component.sensor == 'gaze' and component.conn_type == 'DIRECT':
                self.gaze_sensor_url = component.url
        elif isinstance(component, Event):
            adapted_event = EventAdapter(component)
            await self.event_queue.put(adapted_event)

    async def make_status_update_notifier(self):
        async with Device.from_discovered_device(self.device_info) as device:
            self.notifier = StatusUpdateNotifier(device, callbacks=[self.on_update])
            await self.notifier.receive_updates_start()

    async def cleanup(self):
        await self.notifier.receive_updates_stop()


class EventAdapter:
    def __init__(self, sample):
        self.name = sample.name
        self.timestamp_unix_ns = sample.timestamp
        self.timestamp_unix_seconds = self.timestamp_unix_ns * 1e-9


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


# send events in intervals
async def send_events_in_interval(device_info, sec=60):
    n_events_sent = 0
    while True:
        await send_timesync_event(device_info, f'lsl.time_sync.{n_events_sent}')
        await asyncio.sleep(sec)
        n_events_sent += 1
        logger.debug(f'sent time synchronization event no {n_events_sent}')


async def send_timesync_event(device_info, message: str):
    async with Device.from_discovered_device(device_info) as device:
        await device.send_event(message)
