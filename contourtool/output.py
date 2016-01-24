"""
Part of contourtool.py - read data from Contour Next USB blood glucose meters
Copyright (C) 2016 Ben Jones <benj2579@gmail.com>
See the COPYING file for licence information.
"""

# small classes for record output

import csv
from . import astm


def convert_unit(type, from_value, from_unit, args):
    """
    Convert a value to preferred units and round to one decimal place.
    """
    mg_dl_per_mmol_l = 18.015768
    to_unit = {
        "Glucose": args.glucose_units,
        "Carb": args.carb_units,
        "Insulin": "u",
    }[type]
    if type == "Carb":
        from_unit = {
            "0": "unknown",
            "1": "g",
            "2": "points",
            "3": "choices"
        }[from_unit]
    if type == "Insulin":
        # The unit code specifies the type of insulin, but the actual
        # readings always seem to be in fixed units of 0.1U.
        from_unit = ".1u"
    conversions = {
        ('mmol/l', 'mg/dl'): lambda v: v * mg_dl_per_mmol_l,
        ('mg/dl', 'mmol/l'): lambda v: v / mg_dl_per_mmol_l,
        ('points', 'g'): lambda v: v * args.g_per_point,
        ('g', 'points'): lambda v: v / args.g_per_point,
        ('choices', 'g'): lambda v: v * args.g_per_choice,
        ('g', 'choices'): lambda v: v / args.g_per_choice,
        ('.1u', 'u'): lambda v: v / 10.0,
    }
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()

    if from_unit == to_unit:
        return from_value

    try:
        from_value = float(from_value)
        to_value = conversions[from_unit, to_unit](from_value)
        return "{:.1f}".format(to_value)
    except KeyError:
        raise ValueError("Don't know how to convert from {} to {}".format(
            from_unit, to_unit))


def parse_record_id(record_id):
    if record_id.startswith("^^^"):
        return record_id.lstrip("^")
    else:
        raise astm.FormatError(
            "Bad record ID field in result record")


def parse_timestamp(timestamp):
    if len(timestamp) == 12 and timestamp.isdigit():
        return "{year}-{month}-{day} {hour}:{minute}".format(
            year=timestamp[:4],
            month=timestamp[4:6],
            day=timestamp[6:8],
            hour=timestamp[8:10],
            minute=timestamp[10:12])
    else:
        raise astm.FormatError(
            "Malformed timestamp '{}'".format(timestamp))


class Output(object):
    def __init__(self, args):
        self.args = args

    def parse_record(self, record):
        if record.fields.type != "R":
            raise astm.FormatError(
                "Bad record type: {}".format(record.fields.type))

        value = record.fields.value
        result_type = parse_record_id(record.fields.record_id)
        units, ref = record.fields.units_ref.split("^")
        markers = set(record.fields.markers.split("/"))

        if "C" in markers:
            # This is a result from a control solution, so don't
            # include it.
            return

        if not((result_type == "Glucose" and ref == "P") or
               (result_type != "Glucose" and ref == "")):
            raise astm.FormatError(
                "Unexpected reference method '{ref}'"
                " for result type '{type}'".format(
                    ref=ref, type=result_type))

        if result_type in set(["Glucose", "Carb", "Insulin"]):
            value = convert_unit(result_type, value, units, self.args)
        else:
            raise astm.FormatError(
                "Unknown result type '{}'".format(result_type))

        if result_type == "Insulin":
            # use different result types for different insulins
            result_type = "{insulin_type}Insulin".format(
                insulin_type={
                    "0": "Unknown",
                    "1": "FastActing",
                    "2": "LongActing",
                    "3": "Mixed"
                }[units])

        fields = {
            "Sequence": record.fields.sequence,
            "Type": result_type,
            "Value": value,
            "Timestamp": parse_timestamp(record.fields.timestamp),
        }

        if result_type == "Glucose":
            marker_fields = {
                "BelowScale": "<" in markers,
                "AboveScale": ">" in markers,
                "BeforeMeal": "B" in markers,
                "AfterMeal": "A" in markers,
                "DontFeelRight": "D" in markers,
                "Fasting": "F" in markers,
                "Sick": "I" in markers,
                "Stress": "S" in markers,
                "Activity": "X" in markers,
                # There are also M and T markers which have hex digits
                # attached - not sure what these mean?
            }

            hours = None
            for marker in markers:
                if marker.startswith("Z"):
                    if hours is not None:
                        raise astm.FormatError(
                            "Multiple Z markers with different values")
                    # hex digit in units of hours/4
                    hours = int(marker[1:], 16) / 4.0
            if hours is not None:
                marker_fields["HoursAfterMeal"] = hours
            fields.update(marker_fields)

        return fields


class CSV(Output):
    def __init__(self, args):
        super(CSV, self).__init__(args)
        self.writer = csv.DictWriter(
            args.output,
            fieldnames=["Sequence", "Timestamp", "Type", "Value",
                        "BelowScale", "AboveScale", "BeforeMeal", "AfterMeal",
                        "DontFeelRight", "Fasting", "Sick", "Stress",
                        "Activity", "HoursAfterMeal"])
        self.writer.writeheader()

    def write_record(self, record):
        fields = self.parse_record(record)
        self.writer.writerow(fields)
