import asyncio
import concurrent.futures
import logging
import time

import click
from pupil_labs.realtime_api.device import Device
from pupil_labs.realtime_api.discovery import Network
from rich import print
from rich.console import group
from rich.live import Live
from rich.logging import RichHandler
from rich.table import Table

from pupil_labs.invisible_lsl_relay import relay

logger = logging.getLogger(__name__)


async def main_async(
    device_address: str = None,
    outlet_prefix: str = None,
    time_sync_interval: int = 60,
    timeout: int = 10,
):
    try:
        if device_address:
            device_ip_address, device_port = get_user_defined_device(device_address)
        else:
            discoverer = DeviceDiscoverer(timeout)
            device_ip_address, device_port = await discoverer.get_device_from_list()
        device_identifier, world_camera_serial = await get_device_info_for_outlet(
            device_ip_address, device_port
        )
        adapter = relay.Relay(
            device_ip=device_ip_address,
            device_port=device_port,
            device_identifier=device_identifier,
            outlet_prefix=outlet_prefix,
            world_camera_serial=world_camera_serial,
        )
        await adapter.relay_receiver_to_publisher(time_sync_interval)
    except TimeoutError:
        logger.error(
            'Make sure your device is connected to the same network.', exc_info=True
        )
    finally:
        logger.info('The LSL stream was closed.')


class DeviceDiscoverer:
    def __init__(self, search_timeout):
        self.selected_device_info = None
        self.search_timeout = search_timeout
        self.n_reload = 0

    async def get_device_from_list(self):
        async with Network() as network:
            with Live(
                "[blue]Looking for devices in your network...",
                auto_refresh=False,
                redirect_stdout=False,
            ) as live:
                await network.wait_for_new_device(timeout_seconds=self.search_timeout)
                while self.selected_device_info is None:
                    live.update(print_device_list(network, self.n_reload), refresh=True)
                    self.n_reload += 1
                    user_input = await input_async()
                    self.selected_device_info = evaluate_user_input(
                        user_input, network.devices
                    )
            logger.info(f"Connecting to {self.selected_device_info}")
        return self.selected_device_info.addresses[0], self.selected_device_info.port


def get_user_defined_device(device_address):
    try:
        address, port = device_address.split(':')
        port = int(port)
        if address == "":
            raise ValueError("Empty address")
        return address, port
    except ValueError as exc:
        raise ValueError(
            'Device address could not be parsed in IP and port!\n '
            'Please provide the address in the format IP:port'
        ) from exc


async def get_device_info_for_outlet(device_ip, device_port):
    async with Device(device_ip, device_port) as device:
        try:
            status = await asyncio.wait_for(device.get_status(), 10)
        except asyncio.TimeoutError as exc:
            logger.error(
                'This ip address was not found in the network. '
                'Please check for typos and make sure the device '
                'is connected to the same network.'
            )
            raise exc
        if not status.hardware.world_camera_serial:
            logger.warning('The world camera is not connected.')
        world_camera_serial = status.hardware.world_camera_serial or 'default'
        return status.phone.device_id, world_camera_serial


async def input_async():
    # based on https://gist.github.com/delivrance/675a4295ce7dc70f0ce0b164fcdbd798?
    # permalink_comment_id=3590322#gistcomment-3590322
    with concurrent.futures.ThreadPoolExecutor(1, 'AsyncInput') as executor:
        user_input = await asyncio.get_event_loop().run_in_executor(
            executor, input, ">>>"
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


@group()
def print_device_list(network, n_reload):
    yield ""
    table = Table(title="Available Pupil Invisible Devices")
    table.add_column("Index", style="blue")
    table.add_column("Address")
    table.add_column("Name")
    for device_index, device_info in enumerate(network.devices):
        ip = device_info.addresses[0]
        port = device_info.port
        full_name = device_info.name
        name = full_name.split(":")[1]
        table.add_row(str(device_index), f"{ip}:{port}", name)
    yield table
    yield (
        "[green] Select [/green] Enter [blue]index[/blue] and hit "
        "[magenta]enter[/magenta]"
    )
    yield "[green] Reload [/green] Hit [magenta]enter[/magenta] without input"
    yield (
        "[yellow]  Abort [/yellow] Use [magenta]ctrl+c[/magenta] and hit "
        "[magenta]enter[/magenta]"
    )
    if n_reload >= 5:
        yield (
            "[yellow]Can't find the device you're looking for?\n"
            "Make sure the Companion App is connected to the same "
            "network and at least version [bold]v1.4.14."
        )
    yield ""


def logger_setup(file_name, debug_level=logging.DEBUG):
    logging.basicConfig(
        level=debug_level,
        filename=file_name,
        format='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
    )
    # set up console logging
    stream_handler = RichHandler(level="INFO")
    formatter = logging.Formatter('%(message)s')
    stream_handler.setFormatter(formatter)
    logging.getLogger().addHandler(stream_handler)


def epoch_is(year, month, day):
    epoch = time.gmtime(0)
    return epoch.tm_year == year and epoch.tm_mon == month and epoch.tm_mday == day


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
@click.option(
    "--log_file_name",
    default="pi_lsl_relay.log",
    help="Name and path where the log file is saved.",
)
@click.option(
    "--device_address",
    help="Specify the ip address and port of the pupil invisible device "
    "you want to relay.",
)
@click.option(
    "--outlet_prefix",
    default="pupil_invisible",
    help="Pass optional names to the lsl outlets.",
)
def relay_setup_and_start(
    device_address: str,
    outlet_prefix: str,
    log_file_name: str,
    timeout: int,
    time_sync_interval: int,
):
    try:
        logger_setup(log_file_name)

        # check epoch time
        assert epoch_is(
            year=1970, month=1, day=1
        ), f"Unexpected epoch: {time.gmtime(0)}"

        asyncio.run(
            main_async(
                device_address=device_address,
                outlet_prefix=outlet_prefix,
                time_sync_interval=time_sync_interval,
                timeout=timeout,
            ),
            debug=False,
        )
    except KeyboardInterrupt:
        logger.info("The relay was closed via keyboard interrupt")
    finally:
        logging.shutdown()
