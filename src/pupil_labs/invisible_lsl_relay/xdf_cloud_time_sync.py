import logging
import re
import traceback
from pathlib import Path
from typing import Collection, Dict, Iterable, NamedTuple

import click
import numpy as np
import pandas as pd
import pyxdf

from .cli import logger_setup
from .linear_time_model import perform_time_alignment

logger = logging.getLogger(__name__)
event_column_name = 'name'
event_column_timestamp = 'timestamp [s]'


@click.command()
@click.argument(
    'path_to_xdf',
    nargs=1,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
@click.argument(
    'paths_to_exports',
    nargs=-1,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
def main(path_to_xdf: Path, paths_to_exports: Collection[Path]):
    # set the logging
    logger_setup('./time_sync_posthoc.log')

    if len(paths_to_exports) == 0:
        logger.info('No paths to exports provided. Looking inside current directory.')
        paths_to_exports = (Path(),)

    align_and_save_data(path_to_xdf, paths_to_exports)


def align_and_save_data(path_to_xdf: Path, paths_to_cloud: Iterable[Path]):
    xdf_events = load_session_id_to_xdf_event_mapping(path_to_xdf)
    for cloud_path in paths_to_cloud:
        cloud_events = load_session_id_to_cloud_exports_mapping(cloud_path)

        common_session_ids = xdf_events.keys() & cloud_events.keys()
        for session_id in common_session_ids:
            logger.info(f"Processing session {session_id}")
            xdf_event_data = xdf_events[session_id]
            cloud_event_info = cloud_events[session_id]  # TODO: find a better name

            xdf_event_data, cloud_event_data = _filter_common_events(
                _PairedDataFrames(xdf_event_data, cloud_event_info.data),
                event_column_name,
            )

            result = perform_time_alignment(
                xdf_event_data, cloud_event_data, event_column_timestamp
            )
            result_path = cloud_event_info.directory / "time_alignment_parameters.json"
            logger.info(f"Writing time alignment parameters to {result_path}")
            result.to_json(result_path)


def load_session_id_to_xdf_event_mapping(path_to_xdf: Path) -> Dict[str, pd.DataFrame]:

    mapping: Dict[str, pd.DataFrame] = {}
    data, _ = pyxdf.load_xdf(path_to_xdf, select_streams=[{'type': 'Event'}])

    for x in data:
        try:
            session_id: str = x['info']['desc'][0]['acquisition'][0]['session_id'][0]
            mapping[session_id] = _xdf_events_to_dataframe(x)
        except KeyError:
            logger.debug(f"Skipping non-Pupil-Invisible stream {x['info']['desc']}")

    if not mapping:
        raise ValueError(
            "xdf file does not contain any valid Pupil Invisible event streams"
        )

    return mapping


class CloudExportEvents(NamedTuple):
    directory: Path
    data: pd.DataFrame


def load_session_id_to_cloud_exports_mapping(
    search_root_path: Path,
) -> Dict[str, CloudExportEvents]:
    results: Dict[str, CloudExportEvents] = {}
    for events_path in search_root_path.rglob("events.csv"):
        data = pd.read_csv(events_path)
        try:
            session_id = _extract_session_id_from_cloud_export_events(data)
        except ValueError:
            logger.warning(f"Could not extract session id from {events_path}")
            logger.debug(traceback.format_exc())
            continue
        results[session_id] = CloudExportEvents(events_path.parent, data)
    return results


def _extract_session_id_from_cloud_export_events(data: pd.DataFrame) -> str:
    pattern = re.compile(
        r"lsl\.time_sync\."  # LSL event name prefix
        r"(?P<session_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
        r"\.\d+"  # counter
    )
    names: pd.Series[str] = data[event_column_name]
    lsl_events = names.loc[names.str.fullmatch(pattern)]
    if lsl_events.empty:
        raise ValueError(
            "No events found that matched the LSL Relay pattern "
            "(lsl.time_sync.<uuid>.<counter>)"
        )
    first_event: str = lsl_events.iloc[0]
    result = re.match(pattern, first_event)
    if not result:
        raise Exception(
            "This exception should never be reached since the events have been "
            "filtered by the same pattern beforehand"
        )
    session_id = result.group("session_id")
    return session_id


class _PairedDataFrames(NamedTuple):
    left: pd.DataFrame
    right: pd.DataFrame


def _filter_common_events(
    data_frames: _PairedDataFrames, column: str
) -> _PairedDataFrames:

    col_left = data_frames.left[column]
    col_right = data_frames.right[column]

    col_value_intersection = np.intersect1d(col_left, col_right)

    # filter timestamps by the event intersection
    filtered_left = data_frames.left[col_left.isin(col_value_intersection)]
    filtered_right = data_frames.right[col_right.isin(col_value_intersection)]

    return _PairedDataFrames(filtered_left, filtered_right)


def _xdf_events_to_dataframe(
    event_stream, label_data=event_column_name, label_time=event_column_timestamp
):
    return pd.DataFrame(
        {
            label_data: [name[0] for name in event_stream['time_series']],
            label_time: event_stream['time_stamps'],
        }
    )


if __name__ == '__main__':
    main()
