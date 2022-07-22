2.1.1
#####
- Add command line tool for lsl-to-cloud time alignment and vice versa
- Change the events sent for time alignment to include a unique session id

2.1.0
#####
- Add check for correct epoch
- Allow for direct device selection through command line argument
- Outlet prefix can be set though command line argument
- Restructure relay module to accept device ip and port explicitly, instead of accepting DiscoveredDeviceInfo
- Add an acquisition field to the outlet metadata, including manufacturer, model, version and the
  serial number of the world camera

2.0.2
#####
- Fix default duration of network search (10 seconds)
- Fix default interval for time synchronization events (60 seconds)

2.0.1
#####
- Document minimum Pupil Invisible Companion version required (v1.4.14)
- Add code example demonstrating post-hoc time sync between a Pupil Cloud download and
  a LSL recording
- Write debug logs to log file (path defined via ``--log_file_name`` parameter)

  - Requires `click <https://pypi.org/project/click/>`_ instead of `asyncclick
    <https://pypi.org/project/asyncclick/>`_

2.0.0
#####
- First release supporting the `Pupil Labs Network API <https://github.com/pupil-labs/realtime-network-api>`_
- The legacy NDSI-based relay application can be found
  `here <https://github.com/labstreaminglayer/App-PupilLabs/tree/legacy-pi-lsl-relay/pupil_invisible_lsl_relay>`_

- Pull project skeleton from `<https://github.com/pupil-labs/python-module-skeleton>`_
- Initial fork from `<https://github.com/labstreaminglayer/App-PupilLabs>`_
