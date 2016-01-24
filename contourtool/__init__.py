#!/usr/bin/env python2.7

"""
contourtool.py - read data from Contour Next USB blood glucose meters
Copyright (C) 2016 Ben Jones <benj2579@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import print_function

import sys
import usb
import argparse
from . import astm, controlchars, meter, output


__version__ = '0.1'


def print_error(msg, kind="error"):
    print("{kind}: {msg}".format(kind=kind, msg=msg), file=sys.stderr)


def print_header(header, args, file=sys.stderr):
    product, versions, serial, sku = header.fields.sender_id.split("^")
    if product != "Bayer7410":
        raise IOError("Unsupported product ID '{}'".format(product))
    if header.fields.processing_id != "P":
        raise IOError("Invalid processing ID '{}'".format(header.processing_id))
    if args.info:
        print("Product: {product}".format(product=product), file=file)
        print("Versions: {0}, {1}, {2}".format(
            *versions.split("\\")), file=file)
        print("Serial: {}".format(serial), file=file)
        print("SKU: {}".format(sku), file=file)
        print(header.format("{nr_results} results on meter"), file=file)


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve data from a connected Contour Next USB meter"
        " and write to a CSV file.",
        epilog="NOTE: This program is experimental software, not developed"
        " or supported by Bayer. It might damage your meter or render it"
        " unreliable."
        " See the README.rst file for more information and bug reporting"
        " instructions.")

    output_group = parser.add_argument_group("output")
    output_group.add_argument(
        "-o", "--output", type=argparse.FileType("w"), default=sys.stdout,
        help="output file (default stdout)")

    units_group = parser.add_argument_group("units")
    units_group.add_argument(
        "--glucose-units", default="mmol/l",
        choices=set(["mmol/l", "mg/dl"]),
        help="set preferred glucose units for output (default mmol/l)")
    units_group.add_argument(
        "--carb-units", default="g",
        choices=set(["g", "points", "choices"]),
        help="set preferred carb units for output (default g)")
    units_group.add_argument(
        "--g-per-point", default=10.0, type=float, metavar="GRAMS",
        help="set grams per carbohydrate point (default 10)")
    units_group.add_argument(
        "--g-per-choice", default=15.0, type=float, metavar="GRAMS",
        help="set grams per carbohydrate choice (default 15)")

    debug_group = parser.add_argument_group("debugging")
    debug_group.add_argument(
        "-v", dest="verbosity", default=0, action="count",
        help="increase verbosity (repeat for more, up to -vvv)")
    debug_group.add_argument(
        "--info", action="store_true", help="show header record")
    debug_group.add_argument(
        "--astm-dump", type=argparse.FileType("wb"), metavar="FILE",
        help="dump raw ASTM frames to this file")
    debug_group.add_argument(
        "--version", action='version', version='%(prog)s ' + __version__)

    args = parser.parse_args()
    success = False

    try:
        m = meter.NextUSB(args)
        out = output.CSV(args)

        # initialise
        m.init()
        header = m.read_frame()
        print_header(header.get_record(), args)
        m.expect(controlchars.ENQ)
        m.acknowledge()

        # read data
        while True:
            frame = m.read_frame()
            if args.astm_dump is not None:
                args.astm_dump.write(frame.raw_data)
            record = frame.get_record()
            if record.fields.type == "R":
                out.write_record(record)
            m.acknowledge()
            if frame.is_end_frame():
                if record.fields.type != "L":
                    raise IOError("End frame is not a termination record")
                if record.fields.termination_code != "N":
                    raise IOError("Abnormal termination, data might be bad")
                m.expect(controlchars.EOT)
                break

        args.output.close()
        success = True
    except IOError as e:
        print_error(e, "IO or protocol error")
    except astm.FormatError as e:
        print_error(e, "bad data from meter")
        print(
            "Please report a bug (with --astm-dump if possible). Thanks!",
            file=sys.stderr)
    except astm.ChecksumError as e:
        print_error(e, "bad checksum")
    except ValueError as e:
        print_error(e, "internal error")

    return 0 if success else 1
