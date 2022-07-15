import json
import logging
import pathlib

import click
import pyxdf

import pupil_labs.invisible_lsl_relay.linear_time_model as lm_time

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
@click.option(
    '--output_path',
    default='.',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
def main(path_to_xdf, paths_to_exports, output_path):
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

    if not output_path.endswith('/'):
        output_path += '/'

    align_and_save_data(path_to_xdf, paths_to_exports, output_path)


def align_and_save_data(path_to_xdf, paths_to_cloud, output_path):
    # load the xdf file
    try:
        xdf_head, xdf_data = pyxdf.load_xdf(
            path_to_xdf, select_streams=[{'type': 'Gaze'}]
        )
    except Exception:
        raise OSError(f"Invalid xdf file {path_to_xdf}")
    # extract all serial numbers from gaze streams
    xdf_serial_nums = extract_serial_num_from_xdf(xdf_head)
    # check cloud export paths
    for path in paths_to_cloud:
        for info_path in pathlib.Path(path).rglob("info.json"):
            serial_num_found_in_xdf, serial_num = json_serial_in_xdf(
                info_path, xdf_serial_nums
            )
            if serial_num_found_in_xdf:
                logger.debug(f'found serial number {serial_num}')
                (
                    cloud_aligned_time,
                    cloud_to_lsl_mapper,
                    lsl_to_cloud_mapper,
                ) = lm_time.perform_time_alignment(
                    path_to_xdf, info_path.parent, serial_num
                )
                save_files(
                    cloud_aligned_time,
                    cloud_to_lsl_mapper,
                    lsl_to_cloud_mapper,
                    output_path,
                )


def json_serial_in_xdf(path_infojson, xdf_serial_nums):
    with open(path_infojson) as infojson:
        data_infojson = json.load(infojson)
        serial_infojson = extract_serial_num_from_infojson(data_infojson)
        if serial_infojson in xdf_serial_nums:
            return True, serial_infojson
    return False, None


def extract_serial_num_from_xdf(xdf_head):
    camera_serial_nums = []
    for x in xdf_head:
        try:
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


def save_files(cloud_aligned_time, cloud_to_lsl, lsl_to_cloud, output_path):
    cloud_aligned_time.to_csv(output_path + 'gaze.csv')

    mapping_parameters = write_mapper_to_file(cloud_to_lsl, lsl_to_cloud)
    with open(output_path + 'parameters.json', 'w') as out_file:
        json.dump(mapping_parameters, out_file, indent=4)


def write_mapper_to_file(cloud_to_lsl, lsl_to_cloud):
    mapping_parameters = {
        'cloud_to_lsl': {
            'intercept': cloud_to_lsl.intercept_,
            'slope': cloud_to_lsl.coef_[0],
        },
        'lsl_to_cloud': {
            'intercept': lsl_to_cloud.intercept_,
            'slope': lsl_to_cloud.coef_[0],
        },
        'info': {
            'model_type': type(cloud_to_lsl).__name__,
        },
    }
    return mapping_parameters


if __name__ == '__main__':
    main()
