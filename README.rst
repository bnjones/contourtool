Experimental tool to dump data from a Bayer Contour Next USB meter
==================================================================

Introduction
------------

This tool communicates with a Bayer Contour Next USB blood glucose
meter. It dumps data stored on the device to a CSV file.


Important safety information
----------------------------

**This program is experimental software, not developed or supported by
Bayer. It might damage your meter or render it unreliable. Use this
software at your own risk. You have been warned!**


Compatibility
-------------

Only the Contour Next USB meter is currently supported. Other meters
(including earlier Contour meters) are not supported.


Dependencies
------------

- Python 2.7
- PyUSB 0.4 or 1.0


Getting started
---------------

1. Install with ``setup.py``::

     python setup.py install

2. (Optional) Install the udev rules file (for Linux distributions
   using udev)::

     sudo cp udev/50-contour.rules /etc/udev/rules.d/

3. Plug the meter into the USB port and wait for it to enter charging
   mode.

4. Run::

     contourtool -o results.csv

5. When the tool exits, unplug the meter.

6. Check the result.csv file against the results you see in the
   logbook on the meter.


The output file
---------------

The output file is in CSV format, with the following columns:

:Sequence:
   Sequence number for the record. This is provided by the meter.
:Timestamp:
   Date and time as recorded by the meter in YYYY-MM-DD HH:MM format.
:Type:
   One of: ``Glucose``, ``Carb``, ``FastActingInsulin``, ``LongActingInsulin``,
   ``MixedInsulin``.
:Value:
   Value of the reading. For insulin, this is in insulin units. For
   glucose or carbohydrate, the units are selected by the
   ``--glucose-units`` and ``--carb-units`` options. The defaults are
   mmol/l and grams. The units options don't change anything on the
   meter, they're just for output.
:BeforeMeal, AfterMeal, etc:
   For glucose results, each marker ("Notes" on the meter) gets a
   column with a number (for time after meal) or True/False (for all
   the other notes). For non-glucose results these columns are blank.


Known issues
------------

Permissions problems
````````````````````

The example udev rules file ``udev/50-contour.rules`` makes the meter
accessible to the ``plugdev`` group. Depending on your setup, this
might need customisation.

``Expected to see '\x05'``
``````````````````````````

This happens if you run the tool twice, without unplugging the meter
in between. The tool can't currently handle this.

Meter displays ``E86: Software error``
``````````````````````````````````````

If the tool aborts with an error, or takes too long to acknowledge
data, the meter will usually enter this state. It's not permanent and
will go away if you unplug and replug.


Reporting bugs
--------------

Bug reports or feature requests are very welcome. Please report them
to https://github.com/bnjones/contourtool/issues.
