import pylsl
from rich import print
from rich.syntax import Syntax
from rich.table import Table


def main():
    streams = pylsl.resolve_streams()
    if not streams:
        print("[red]ERROR: No streams found")
        return

    table = Table()
    table.add_column("Outlet Name")
    table.add_column("Host")
    table.add_column("Description")
    for stream in streams:
        info = pylsl.StreamInlet(stream).info()
        table.add_row(info.name(), info.hostname(), Syntax(info.as_xml(), "xml"))
    print(table)


if __name__ == "__main__":
    main()
