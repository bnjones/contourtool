"""
Part of contourtool.py - read data from Contour Next USB blood glucose meters
Copyright (C) 2016 Ben Jones <benj2579@gmail.com>
See the COPYING file for licence information.
"""

# Most of this file implements features that PyUSB 1.0 already
# provides. However, several distros ship PyUSB 0.4.3, and newer
# versions of PyUSB can emulate the legacy API, so it makes sense to
# use the 0.4 API for now.
import usb


def find_device(vendor, product):
    for bus in usb.busses():
        for device in bus.devices:
            if device.idVendor == vendor and device.idProduct == product:
                return device
    raise IOError(
        "No device with vendor={:#x} and product={:#x}".format(
            vendor, product))


def find_contour_hid_interface(device):
    if len(device.configurations) != 1:
        raise IOError("Expected 1 configuration, device has {}".format(
            len(device.configurations)))

    config = device.configurations[0]

    if isinstance(config.interfaces[0], list):
        # If we're using PyUSB 1.0 through its backwards-compatible
        # legacy interface, it looks like there's a small
        # incompatibility. In 0.4 config.interfaces is a tuple of
        # interfaces, each of which is a tuple representing alternate
        # settings for that interface. In the 1.0 legacy API, it looks
        # like config.interfaces is a list of sets of interfaces
        # grouped by alternate setting.
        if len(config.interfaces) != 1:
            raise IOError(
                "Expected no alternate settings, but found some"
                " (using PyUSB legacy API emulation)")
        config.interfaces = [
            (interface,) for interface in config.interfaces[0]]

    if len(config.interfaces) != 2:
        raise IOError("Expected 2 interfaces, device has {}".format(
            len(config.interfaces)))

    for interface_alts in config.interfaces:
        if len(interface_alts) != 1:
            raise IOError("Expected no alternate settings, but found some")
        interface = interface_alts[0]
        if interface.interfaceClass == usb.CLASS_HID:
            return interface
        elif interface.interfaceClass == usb.CLASS_MASS_STORAGE:
            # There's also a mass storage interface which is used to
            # expose the software shipped with the meter.
            pass
        else:
            raise IOError("Unexpected interface class {}".format(
                interface.interfaceClass))


def find_endpoints(interface):
    # We're expecting a HID interface with one IN and one OUT
    # endpoint. Check that this is what we've got and return the
    # endpoints.
    if interface.interfaceClass != usb.CLASS_HID:
        raise IOError("Not a HID interface")

    in_endpoint = None
    out_endpoint = None

    for ep in interface.endpoints:
        if ep.address & usb.ENDPOINT_IN:
            if in_endpoint is None:
                in_endpoint = ep
            else:
                raise IOError("More than one IN endpoint")
        else:
            if out_endpoint is None:
                out_endpoint = ep
            else:
                raise IOError("More than one OUT endpoint")

    return in_endpoint, out_endpoint


def dump_endpoint(dump, ep, desc):
    dump("Endpoint '{}': {:#x}".format(desc, ep.address))
    dump("  interval: {}".format(ep.interval))
    dump("  type: {}".format(
        {
            usb.ENDPOINT_TYPE_CONTROL: 'control',
            usb.ENDPOINT_TYPE_ISOCHRONOUS: 'isochronous',
            usb.ENDPOINT_TYPE_INTERRUPT: 'interrupt',
            usb.ENDPOINT_TYPE_BULK: 'bulk'
        }[ep.type]))
    dump("  maxPacketSize: {}".format(ep.maxPacketSize))
