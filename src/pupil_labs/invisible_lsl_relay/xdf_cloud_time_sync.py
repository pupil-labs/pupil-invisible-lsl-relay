import json
import logging
import pathlib

import click
import pyxdf

logger = logging.getLogger(__name__)


@click.command()
@click.argument(
    'path_to_xdf', nargs=1, type=click.Path(exists=True, file_okay=True, dir_okay=False)
)
@click.argument(
    'paths_to_exports',
    nargs=-1,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
def main(path_to_xdf, paths_to_exports):
    # set the logging
    logging.basicConfig(
        level=logging.DEBUG,
        filename='./time_sync_posthoc.log',
        format='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
    )
    # set up console logging
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)s\t| %(levelname)s\t| %(message)s')
    stream_handler.setFormatter(formatter)

    logging.getLogger().addHandler(stream_handler)

    if len(paths_to_exports) == 0:
        logger.info('No paths to exports provided. Looking inside current directory.')
        paths_to_exports = ['.']
    load_files(path_to_xdf, paths_to_exports)


def load_files(path_to_xdf, paths_to_export):
    # load the xdf file
    try:
        xdf_head, xdf_data = pyxdf.load_xdf(path_to_xdf)
    except Exception:
        raise OSError(f"Invalid xdf file {path_to_xdf}")
    # extract all serial numbers from gaze streams
    xdf_serial_nums = extract_serial_num_from_xdf(xdf_head)
    # check cloud export paths
    for path in paths_to_export:
        for info_path in pathlib.Path(path).rglob("info.json"):
            if json_serial_in_xdf(info_path, xdf_serial_nums):
                perform_time_alignment(path_to_xdf, info_path.parent)


def perform_time_alignment(xdf_path, recording_dir):
    print(f'perform time alignment between {xdf_path} and {recording_dir}')
    save_files()


def json_serial_in_xdf(path_infojson, xdf_serial_nums):
    with open(path_infojson) as infojson:
        data_infojson = json.load(infojson)
        if extract_serial_num_from_infojson(data_infojson) in xdf_serial_nums:
            return True
    return False


def extract_serial_num_from_xdf(xdf_head):
    camera_serial_nums = []
    for x in xdf_head:
        try:
            if x['info']['type'][0] == 'Gaze':
                xdf_camera_serial = x['info']['desc'][0]['acquisition'][0][
                    'world_camera_serial'
                ][0]
                camera_serial_nums.append(xdf_camera_serial)
        except KeyError as e:
            raise KeyError(
                "The xdf file does not contain the expected fields. "
                "Make sure it's been streamed with the Pupil Invisible "
                "LSL Relay version 2.1.0 or higher."
            ) from e
    return camera_serial_nums


def extract_serial_num_from_infojson(data_infojson):
    try:
        cloud_camera_serial = data_infojson['scene_camera_serial_number']
        return cloud_camera_serial
    except KeyError:
        logger.warning(f"Found invalid info.json file at {data_infojson.resolve()}")
        return None


def save_files():
    pass


if __name__ == '__main__':
    main()
