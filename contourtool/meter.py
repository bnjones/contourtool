"""
Part of contourtool.py - read data from Contour Next USB blood glucose meters
Copyright (C) 2016 Ben Jones <benj2579@gmail.com>
See the COPYING file for licence information.
"""

from __future__ import print_function

import sys
import usb
from . import astm, controlchars, usbutil


class NextUSB(object):
    vendor_id = 0x1a79          # Bayer
    product_id = 0x7410         # Contour Next USB

    def __init__(self, args):
        self.debug_categories = set(
            ["usb", "buffering", "commands"][:args.verbosity])
        self.claimed_interface = False
        self.device = usbutil.find_device(self.vendor_id, self.product_id)
        self.interface = usbutil.find_contour_hid_interface(self.device)
        self.in_endpoint, self.out_endpoint = usbutil.find_endpoints(
            self.interface)
        usb_debug = lambda msg: self.debug("usb", msg)
        usbutil.dump_endpoint(usb_debug, self.in_endpoint, 'in')
        usbutil.dump_endpoint(usb_debug, self.out_endpoint, 'out')
        self.handle = self.device.open()
        self.mode = 'data_transfer'
        self.readstack = []

        # If a kernel driver is using the device, try and get the
        # kernel to release it, so it's available for us to use.
        try:
            self.handle.detachKernelDriver(self.interface.interfaceNumber)
        except usb.USBError as e:
            pass # try and carry on anyway

        # Claim the interface we want to use.
        self.handle.claimInterface(self.interface.interfaceNumber)
        self.claimed_interface = True

    def __del__(self):
        if self.claimed_interface:
            self.handle.releaseInterface()

    def debug(self, category, msg):
        if category in self.debug_categories:
            print(msg, file=sys.stderr)

    def read_raw(self):
        """
        Read raw data from the device in interrupt mode
        """
        msg = self.handle.interruptRead(
            self.in_endpoint.address, self.in_endpoint.maxPacketSize)
        # PyUSB returns a tuple of integers representing bytes in the
        # message. Convert to a string.
        data = ''.join([chr(c) for c in msg])
        self.debug("usb", "USB interruptRead: {!r}".format(data))
        return data

    def write_raw(self, data):
        """
        Write raw data to the device in interrupt mode
        """
        self.debug("usb", "USB interruptWrite: {!r}".format(data))
        return self.handle.interruptWrite(self.out_endpoint.address, data)

    def read_bytes(self):
        """
        Read a HID report packet from the device, return bytes after
        stripping prefix/length
        """
        data = self.read_raw()
        # Not sure why the messages start with ABC or what
        # significance it has. This code checks for ABC but that might
        # not be the right thing to do.
        assert data.startswith("ABC")
        length = ord(data[3])
        data = data[4:length + 4]
        self.debug("usb", "Read: {!r}".format(data))
        return data

    def read(self):
        if self.readstack:
            d = self.readstack.pop()
            self.debug("buffering", "return {!r} from unread()".format(d))
            return d
        return self.read_bytes()

    def unread(self, data):
        if data:
            self.debug("buffering", "unread {!r}".format(data))
            self.readstack.append(data)

    def write(self, data):
        """
        Write a HID report packet to the device, given bytes to stuff in
        the packet
        """
        if len(data) > 60:
            raise IOError("data too large to fit in one message, TODO: split")
        self.debug("usb", "Write: {!r}".format(data))
        msg = "ABC{length_byte}{data}".format(
            length_byte=chr(len(data)),
            data=data)
        self.write_raw(msg)

    def read_frame(self):
        """
        Read a complete ASTM frame from the device
        """
        data = self.read()
        while not data.endswith("\r\n"):
            data += self.read()
        if not data.startswith(controlchars.STX):
            raise IOError("Expected STX at start of data")
        self.debug("usb", "Got complete frame: {!r}".format(data))
        frame = astm.Frame(data)
        self.unread(frame.trailer)
        return frame

    def init(self):
        """
        Send an X to the meter to wake it up and make it send a header
        record.
        """
        self.write("X")
        self.expect(controlchars.EOT)  # TODO: handle ENQ

    def acknowledge(self):
        self.write(controlchars.ACK)

    def expect(self, prefix):
        """
        Read data from the device and check that it begins with the given
        string. Return any following data.
        """
        self.debug("usb", "expect {!r}".format(prefix))
        data = self.read()
        if data.startswith(prefix):
            self.unread(data[len(prefix):])
            return data[:len(prefix)]
        else:
            raise IOError("Expected to see {!r}".format(data))

    def enter_mode(self, mode):
        """
        This doesn't work properly
        """
        if self.mode != mode:
            self.debug("commands", "Switching from {} mode to {} mode".format(
                self.mode, mode))
            command_char = {
                "command": controlchars.ENQ,
                "data_transfer": controlchars.CAN,
            }[mode]
            self.write(command_char)

            expect_char = {
                "command": controlchars.ACK,
                "data_transfer": None
            }[mode]
            if expect_char is not None:
                self.expect(expect_char)
            self.mode = mode

    def power_off(self):
        """
        This doesn't work properly
        """
        self.enter_mode("command")
        self.write("E|")
        self.expect(controlchars.ACK)
