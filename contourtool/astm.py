"""
Part of contourtool.py - read data from Contour Next USB blood glucose meters
Copyright (C) 2016 Ben Jones <benj2579@gmail.com>
See the COPYING file for licence information.
"""

# TODO: improve this/replace it with a better external library (e.g.
# python-astm)
from __future__ import print_function

import re
import controlchars
from collections import namedtuple

frame_re = re.compile(
    "\x02"
    "(?P<number>[0-7])"         # frame number: starts at 1, wraps to 0 after 7
    "(?P<data>[^\x03\x17]*?)"   # data
    "(?P<type>[\x03\x17])"      # frame type: ETX = end, ETB = more follows
    "(?P<checksum>[0-9A-Fa-f]{2})"  # 8-bit checksum in hex
    "\r\n",                     # CRLF
    re.DOTALL)


class ASTMError(ValueError): pass
class FormatError(ASTMError): pass
class ChecksumError(ASTMError): pass


class Frame(object):
    def __init__(self, raw_data):
        self.match = frame_re.match(raw_data)
        if not self.match:
            raise FormatError("Malformed ASTM frame")

        self.raw_data = raw_data
        self.trailer = raw_data[self.match.end(0):]
        self.data = self.match.group('data')

        self.checksum = "{:02X}".format(
            self.compute_checksum(
                raw_data[self.match.start('number'):self.match.end('type')]))
        if self.checksum != self.match.group('checksum'):
            raise ChecksumError(
                "Checksum mismatch: {} in frame, computed {}".format(
                    self.match.group('checksum'), self.checksum))

    def compute_checksum(self, data):
        return sum([ord(c) for c in data]) & 0xff

    def is_end_frame(self):
        return self.match.group('type') == controlchars.ETX

    def get_record(self):
        return Record(self.data)

    def __repr__(self):
        return "<ASTM {type} frame {nr}: {data!r}>".format(
            type={
                controlchars.ETX: 'end',
                controlchars.ETB: 'intermediate'
            }[self.match.group('type')],
            nr=self.match.group('number'),
            data=self.match.group('data')[:6]+'...')


class Record(object):
    def __init__(self, raw_data):
        if raw_data.endswith("\r"):
            # The data inside ASTM frames the meter sends always seem
            # to end with a CR, which doesn't seem to be part of the
            # record.
            raw_data = raw_data[:-1]
        self.fields = {
            'H': namedtuple(
                "HeaderRecord",
                "type delimiters unknown1 unknown2 sender_id info nr_results"
                " unknown3 unknown4 unknown5 unknown6 processing_id"
                " spec_version timestamp".split()),
            'P': namedtuple(
                "PatientRecord",
                "type sequence".split()),
            'R': namedtuple(
                "ResultRecord",
                "type sequence record_id value units_ref unknown1 markers"
                " unknown2 timestamp".split()),
            'L': namedtuple(
                "TerminatorRecord",
                "type sequence read_key termination_code".split())
        }[raw_data[0]](*raw_data.split("|"))

    def format(self, template):
        return template.format(**self.fields._asdict())
