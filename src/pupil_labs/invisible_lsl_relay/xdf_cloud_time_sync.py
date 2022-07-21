import json
import logging
import pathlib

import click
import pyxdf

from .cli import logger_setup
from .linear_time_model import perform_time_alignment

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
    logger_setup('./time_sync_posthoc.log')

    if len(paths_to_exports) == 0:
        logger.info('No paths to exports provided. Looking inside current directory.')
        paths_to_exports = ['.']

    output_path = pathlib.Path(output_path)
    align_and_save_data(path_to_xdf, paths_to_exports, output_path)


def align_and_save_data(path_to_xdf, paths_to_cloud, output_path):
    # load the xdf file
    try:
        xdf_head, xdf_data = pyxdf.load_xdf(
            path_to_xdf, select_streams=[{'type': 'Event'}]
        )
    except Exception:
        raise OSError(f"Invalid xdf file {path_to_xdf}")
    # extract all serial numbers from gaze streams
    xdf_serial_nums = extract_serial_num_from_xdf(xdf_head)
    if not xdf_serial_nums:
        raise ValueError(
            "xdf file does not contain any valid Pupil Invisible event streams"
        )
    # check cloud export paths
    for path in paths_to_cloud:
        for info_path in pathlib.Path(path).rglob("info.json"):
            try:
                serial_num = extract_json_serial(
                    info_path
                )
                assert serial_num in xdf_serial_nums
            except KeyError:
                # a json.info file without a serial number
                # (probably not from a PI export)
                logger.warning('Skipping invalid info.json file '
                               f'at {info_path.resolve()}')
            except AssertionError:
                # a json.info file with an invalid serial number
                # (from a PI export that was not in the xdf file)
                pass
            else:
                result = perform_time_alignment(
                    path_to_xdf, info_path.parent, serial_num
                )
                save_files(
                    result.cloud_aligned_time,
                    result.cloud_to_lsl,
                    result.lsl_to_cloud,
                    output_path,
                )


def extract_json_serial(path_infojson):
    with open(path_infojson) as infojson:
        data_infojson = json.load(infojson)
        return data_infojson['scene_camera_serial_number']


def extract_serial_num_from_xdf(xdf_head):
    camera_serial_nums = []
    for x in xdf_head:
        try:
            xdf_camera_serial = x['info']['desc'][0]['acquisition'][0][
                'world_camera_serial'
            ][0]
            camera_serial_nums.append(xdf_camera_serial)
        except KeyError:
            logger.debug(f"Skipping non-Pupil-Invisible stream {x['info']['desc']}")
    return camera_serial_nums


def save_files(cloud_aligned_time, cloud_to_lsl, lsl_to_cloud, output_path):
    cloud_aligned_time.to_csv(output_path /'gaze.csv')

    mapping_parameters = mapping_params_to_dict(cloud_to_lsl, lsl_to_cloud)
    with open(output_path/'parameters.json', 'w') as out_file:
        json.dump(mapping_parameters, out_file, indent=4)


def mapping_params_to_dict(cloud_to_lsl, lsl_to_cloud):
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
