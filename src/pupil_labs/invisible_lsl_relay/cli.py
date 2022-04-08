import asyncio
import concurrent.futures
import logging

# async version of click, requires anyio
import asyncclick as click
from pupil_labs.realtime_api.discovery import Network

from pupil_labs.invisible_lsl_relay import relay

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--time_sync_interval",
    default=60,
    help=(
        "Interval in seconds at which time-sync events are sent. "
        "Set to 0 to never send events."
    ),
)
@click.option(
    "--timeout",
    default=10,
    help="Time limit in seconds to try to connect to the device",
)
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


def main_handling_keyboard_interrupt():
    try:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(main_async(), debug=True)
    except KeyboardInterrupt:
        logger.warning("The relay was closed via keyboard interrupt")
