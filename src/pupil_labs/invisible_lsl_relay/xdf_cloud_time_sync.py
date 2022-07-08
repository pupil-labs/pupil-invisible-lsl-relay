import json
import os.path
import pathlib

import click
import pyxdf


@click.command()
@click.argument('path_to_xdf', nargs=1)
@click.argument('paths_to_exports', nargs=-1)
def main(path_to_xdf, paths_to_exports):
    check_input(path_to_xdf, paths_to_exports)
    load_files(path_to_xdf, paths_to_exports)


def check_input(path_to_xdf, paths_to_export):
    if not pathlib.Path(path_to_xdf).is_file():
        # path_to_xdf should be a file with the ending .xdf
        raise FileNotFoundError(f'The path {path_to_xdf} does not point to a file.')
    if not path_to_xdf.endswith('.xdf'):
        raise TypeError(f'The file {path_to_xdf} is not an .xdf file.')

    for path in paths_to_export:
        # each path to an export should be a valid path
        if not pathlib.Path(path).is_dir():
            raise NotADirectoryError(
                'All paths provided after the path '
                'to the xdf file must be valid directories.'
            )


def load_files(path_to_xdf, paths_to_export):
    # load the xdf file
    try:
        xdf_head, xdf_data = pyxdf.load_xdf(path_to_xdf)
    except Exception:
        raise OSError(f"Invalid xdf file {path_to_xdf}")
    for path in paths_to_export:
        for info_path in pathlib.Path(path).rglob("info.json"):
            if check_files(xdf_head, info_path):
                perform_time_alignment(path_to_xdf, os.path.dirname(info_path))


def perform_time_alignment(xdf_path, recording_dir):
    print(f'perform time alignment between {xdf_path} and {recording_dir}')
    save_files()


def check_files(head, path):
    for x in head:
        if x['info']['type'][0] == 'Gaze':
            xdf_camera_serial = x['info']['desc'][0]['acquisition'][0][
                'world_camera_serial'
            ][0]
            with open(path) as file:
                data = json.load(file)
                try:
                    cloud_camera_serial = data['scene_camera_serial_number']
                    if cloud_camera_serial == xdf_camera_serial:
                        return True
                except KeyError:
                    # this is not a pupil info file
                    pass
    return False


def save_files():
    pass


if __name__ == '__main__':
    main()
