.. image:: https://img.shields.io/pypi/v/skeleton.svg
   :target: `PyPI link`_

.. image:: https://img.shields.io/pypi/pyversions/skeleton.svg
   :target: `PyPI link`_

.. _PyPI link: https://pypi.org/project/skeleton

.. image:: https://github.com/jaraco/skeleton/workflows/tests/badge.svg
   :target: https://github.com/jaraco/skeleton/actions?query=workflow%3A%22tests%22
   :alt: tests

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Code style: Black

.. .. image:: https://readthedocs.org/projects/skeleton/badge/?version=latest
..    :target: https://skeleton.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/badge/skeleton-2021-informational
   :target: https://blog.jaraco.com/skeleton

==========================
Pupil Invisible Gaze Relay
==========================

Installation
============

.. code-block:: bash
   git clone https://github.com/labstreaminglayer/App-PupilLabs.git

   cd App-PupilLabs/

   # Use the Python 3 installation of your choice
   python -m pip install -U pip
   python -m pip install -r requirements.txt

Usage
=====

Direct mode
----------

The direct usage of the Pupil Invisible Gaze Relay module is to provide a device host
name as an argument. The module will wait for that device to announce a gaze sensor,
will connect to it and start pushing the gaze data to the LSL outlet named
``pupil_invisible``.

.. code-block:: bash
   pupil_invisible_lsl_relay --host-name <DEVICE_NAME>


Interactive mode
----------------

In interactive mode, there is no need to provide the device name beforehand. Instead,
the module monitors the network and shows a list of available devices which the user can
select.

.. code-block:: bash
   pupil_invisible_lsl_relay
