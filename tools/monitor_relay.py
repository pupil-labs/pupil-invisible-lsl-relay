import contextlib
import time
from collections import deque

import numpy as np
import pylsl
from rich import print
from rich.live import Live
from rich.table import Table


def main():
    streams = [Stream(info) for info in pylsl.resolve_streams()]
    if not streams:
        print("[red]ERROR: No streams found")
        return

    try:
        with Live(generate_table(streams), auto_refresh=False) as live:
            with contextlib.suppress(KeyboardInterrupt):
                while True:
                    time.sleep(0.5)
                    live.update(generate_table(streams), refresh=True)

    finally:
        for stream in streams:
            stream.close()


def generate_table(streams):
    table = Table()
    table.add_column("Outlet Name")
    table.add_column("Host")
    table.add_column("Sample Rate", justify="right")
    for stream in streams:
        stream.add_row_to(table)
    return table


class Stream:
    def __init__(self, info: pylsl.StreamInfo):
        self.info = info
        self.inlet = pylsl.StreamInlet(info)
        self.inlet.open_stream(timeout=10)
        self.ts = deque(maxlen=200)

    def close(self):
        print(f"[dim blue]Closing {self.info.name()} ({self.info.hostname()})")
        self.inlet.flush()
        self.inlet.close_stream()

    def update(self):
        while self.inlet.samples_available():
            _, ts = self.inlet.pull_chunk()
            self.ts.extend(ts)

    def add_row_to(self, table: Table):
        self.update()
        diff = np.diff(self.ts)
        if diff.size:
            rate = 1 / diff.mean()
        else:
            rate = 0
        table.add_row(self.info.name(), self.info.hostname(), f"{rate:.3f} Hz")


if __name__ == "__main__":
    main()
