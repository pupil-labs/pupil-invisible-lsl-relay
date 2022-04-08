***************************************************
Welcome to Pupil Invisible LSL Relay documentation!
***************************************************

Install and Usage
==================
Install the Pupil Invisible Relay with pip::

	pip install pupil-invisible-lsl-relay

After you installed the relay, you can start it by executing::

	python invisible_lsl_relay

The Relay takes two arguments:

**--time_sync_interval** is used to set the interval (in seconds) at which the relay sends events
to the pupil invisible device that can be used for time synchronization. The default is 60 seconds.

**--timeout** is used to defines the maximum time (in seconds) the relay will search the network for new
devices before returning. The default is 10 seconds.


.. toctree::
  :maxdepth: 3
  :glob:

  overview.rst
  api.rst
  history.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
