import asyncio
import concurrent.futures
import logging
import time

import click
from pupil_labs.realtime_api.discovery import Network

from pupil_labs.invisible_lsl_relay import relay

logger = logging.getLogger(__name__)


async def main_async(time_sync_interval: int = 60, timeout: int = 10):
    discoverer = DeviceDiscoverer(timeout)
    try:
        await discoverer.get_user_selected_device()
    except TimeoutError:
        logger.error(
            'Make sure your device is connected to the same network.', exc_info=True
        )
    assert discoverer.selected_device_info
    adapter = relay.Relay(discoverer.selected_device_info)
    await adapter.relay_receiver_to_publisher(time_sync_interval)
    logger.info('The LSL stream was closed.')


class DeviceDiscoverer:
    def __init__(self, search_timeout):
        self.selected_device_info = None
        self.search_timeout = search_timeout
        self.n_reload = 0

    async def get_user_selected_device(self):
        async with Network() as network:
            print("Looking for devices in your network...\n\t", end="")
            await network.wait_for_new_device(timeout_seconds=self.search_timeout)

            while self.selected_device_info is None:
                print("\n======================================")
                print("Please select a Pupil Invisible device by index:")
                print("\tIndex\tAddress" + (" " * 14) + "\tName")
                for device_index, device_info in enumerate(network.devices):
                    ip = device_info.addresses[0]
                    port = device_info.port
                    full_name = device_info.name
                    name = full_name.split(":")[1]
                    print(f"\t{device_index}\t{ip}:{port}\t{name}")

                print()
                print("To reload the list, hit enter. ")
                print("To abort device selection, use 'ctrl+c' and hit 'enter'")
                if self.n_reload >= 5:
                    print(
                        "Can't find the device you're looking for?\n"
                        "Make sure the Companion App is connected to the same "
                        "network and at least version v1.4.14."
                    )
                self.n_reload += 1
                user_input = await input_async()
                self.selected_device_info = evaluate_user_input(
                    user_input, network.devices
                )


async def input_async():
    # based on https://gist.github.com/delivrance/675a4295ce7dc70f0ce0b164fcdbd798?
    # permalink_comment_id=3590322#gistcomment-3590322
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


def epoch_is(year, month, day):
    epoch = time.gmtime(0)
    return epoch.tm_year == year and epoch.tm_mon == month and epoch.tm_mday == day


@click.command()
@click.option(
    "--time_sync_interval",
    default=10,
    help=(
        "Interval in seconds at which time-sync events are sent. "
        "Set to 0 to never send events."
    ),
)
@click.option(
    "--timeout",
    default=60,
    help="Time limit in seconds to try to connect to the device",
)
@click.option(
    "--log_file_name",
    default="pi_lsl_relay.log",
    help="Name and path where the log file is saved.",
)
def relay_setup_and_start(log_file_name: str, timeout: int, time_sync_interval: int):
    try:
        logging.basicConfig(
            level=logging.DEBUG,
            filename=log_file_name,
            format='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
        )
        # set up console logging
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(name)s | %(levelname)s | %(message)s')
        stream_handler.setFormatter(formatter)

        logging.getLogger().addHandler(stream_handler)

        # check epoch time
        assert epoch_is(year=1970, month=1, day=1)

        asyncio.run(
            main_async(time_sync_interval=time_sync_interval, timeout=timeout),
            debug=False,
        )
    except KeyboardInterrupt:
        logger.info("The relay was closed via keyboard interrupt")
    finally:
        logging.shutdown()
