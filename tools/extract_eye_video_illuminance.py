from pathlib import Path
from typing import Collection

import av
import click
import numpy as np
import pandas as pd
from rich import print
from rich.progress import track
from rich.traceback import install as install_rich_traceback


@click.command()
@click.argument(
    "eye_videos",
    type=click.Path(exists=True, readable=True, dir_okay=False, path_type=Path),
    nargs=-1,
)
def main(eye_videos: Collection[Path]):
    if not eye_videos:
        raise ValueError(
            "Please pass at least one path to an `PI right/left v1 ps*.mp4/mjpeg` file."
        )
    for path in eye_videos:
        extract_illuminance(path)


def extract_illuminance(eye_video_path: Path):
    print(f"Processing {eye_video_path}...")
    time = _load_time(eye_video_path.with_suffix(".time"))
    illuminance = _decode_illuminance(eye_video_path, num_expected_frames=time.shape[0])

    output_path = eye_video_path.with_suffix(".illuminance.csv")
    print(f"Writing result to {output_path}")
    pd.concat([illuminance, time], axis="columns").to_csv(output_path, index=False)


def _load_time(time_path: Path) -> "pd.Series[int]":
    return pd.Series(np.fromfile(time_path, dtype="<u8"), name="timestamp [ns]")


def _decode_illuminance(video_path: Path, num_expected_frames: int) -> "pd.Series[int]":
    video_format = video_path.suffix[1:]
    with av.open(str(video_path), format=video_format) as container:
        container.streams.video[0].thread_type = "AUTO"
        illuminance = [
            np.array(frame.planes[0], dtype=np.uint8).sum()
            for frame in track(
                container.decode(video=0),
                description="Decoding illuminance",
                total=num_expected_frames,
            )
        ]
    return pd.Series(illuminance, name="illuminance")


if __name__ == "__main__":
    install_rich_traceback()
    main()
