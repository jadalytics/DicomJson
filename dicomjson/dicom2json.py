#!/usr/bin/env python3

import argparse
import cv2
import json
import logging
import numpy as np
from pathlib import Path
from pydicom import dcmread
from pydicom.errors import InvalidDicomError
from pydicom.dataset import Dataset, FileDataset
from constants import JsonConstants, PngConstants


DEFAULT_OUTPUT_DIR = Path(__file__).parent / Path("output")
# Define Formatter
log_formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s") # pylint: disable=C0103
# Get basic logger
logger = logging.getLogger() # pylint: disable=C0103
logger.setLevel(logging.DEBUG)
# Define output file logger
file_handler = logging.FileHandler('dicom2json.log') # pylint: disable=C0103
file_handler.setFormatter(log_formatter)
# Define output console logger
console_handler = logging.StreamHandler() # pylint: disable=C0103
console_handler.setFormatter(log_formatter)
# Associate console and file loggers to the root logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


def my_json_dumps(data):
    """my_json_dumps
    JSON formatter

    Arguments:
        data {str} -- Data to JSON beautify

    Returns:
        str -- Data beautified
    """
    return json.dumps(data, indent=4, sort_keys=True)


def dicom2json(input_file, remove_dicom_fields):
    """dicom2json
    Convert DICOM file to JSON using pydicom library

    Arguments:
        input_file {str} -- DICOM file location
        remove_dicom_fields {list} -- DICOM field name to not save in JSON
    """
    try:
        dicom_dataset = dcmread(str(input_file))

        # Extract image from PixelData DICOM file
        img_dtype = None
        if dicom_dataset.BitsStored == 8:
            img_dtype = np.uint8
        elif dicom_dataset.BitsStored == 16:
            img_dtype = np.uint16
        else:
            bits_stored_error = "Unrecognized DICOM BitsStored value '{}'".format(
                dicom_dataset.BitsStored)
            raise ValueError(bits_stored_error)

        dicom_image = np.ndarray((dicom_dataset.Rows, dicom_dataset.Columns),
                                 img_dtype,
                                 dicom_dataset.PixelData)

        if remove_dicom_fields:
            for dicom_fields_name in remove_dicom_fields:
                if dicom_dataset.get(dicom_fields_name):
                    dicom_dataset.pop(dicom_fields_name)
                else:
                    dicom_error = "Unrecognized DICOM field named '{}'".format(
                        dicom_fields_name)
                    logger.warning(dicom_error)

        # Convert FileDataset to JSON object
        dicom_dataset_to_json_meta = dicom_dataset.file_meta.to_json_dict()
        dicom_dataset_to_json = dicom_dataset.to_json_dict()

        # Format output filepath
        output_filepath = (DEFAULT_OUTPUT_DIR / dicom_dataset.SOPInstanceUID)
        output_dataset_filepath = output_filepath.with_suffix(
            JsonConstants.SUFFIX.value)
        output_image_filepath = output_filepath.with_suffix(
            PngConstants.SUFFIX.value)
        output_template_filepath = (DEFAULT_OUTPUT_DIR / input_file.stem).with_suffix(
            JsonConstants.SUFFIX.value)

        # Write dataset JSON file
        dicom_json_file = open(str(output_dataset_filepath), "w")
        dicom_json_file.write(my_json_dumps(
            {JsonConstants.META.value: dicom_dataset_to_json_meta,
             JsonConstants.DATA.value: dicom_dataset_to_json}))
        dicom_json_file.close()
        # Write image PNG file
        cv2.imwrite(str(output_image_filepath), dicom_image) # pylint: disable=E1101
        # Write template file
        dicom_json_template_file = open(output_template_filepath, "w")
        dicom_json_template_file.write(my_json_dumps([
            {JsonConstants.TEMPLATE.value: str(output_dataset_filepath),
             JsonConstants.IMAGE.value: str(output_image_filepath),
             JsonConstants.OUTPUT.value: input_file.name}]))
        dicom_json_template_file.close()
        logger.debug("Output files for '%s' have been writed at: '%s'", \
            str(input_file), DEFAULT_OUTPUT_DIR)
    except (FileNotFoundError,
            InvalidDicomError,
            PermissionError,
            UnboundLocalError) as error:
        raise error


def main():
    """main
    Extract all informations from arguments parser
    If all mandatories data are provided, we launch
    the converter

    Returns:
        [int] -- Script exit code
    """
    parser = argparse.ArgumentParser()

    # Positional argument
    parser.add_argument(
        "input_file",
        type=str,
        help="dicom to convert to json")

    # Optionals arguments
    remove_dicom_fields_help = "remove DICOM fields after extraction. \
        The list of possible values is available in the file '_dicom_dict.py' at \
            the root of the folder where the 'Keyword' for each field is specified."
    parser.add_argument(
        "-rdf",
        "--remove_dicom_fields",
        nargs='+',
        type=str,
        help=remove_dicom_fields_help,
        default=None)

    args = parser.parse_args()

    input_filepath = Path(args.input_file)
    if not input_filepath.exists():
        input_not_exists_error = "{} does not exists, abort dicom2json execution!".format(
            input_filepath)
        raise ValueError(input_not_exists_error)
    if not input_filepath.is_file():
        input_is_not_file_error = "{} is not a file, abort dicom2json execution!".format(
            input_filepath)
        raise ValueError(input_is_not_file_error)

    try:
        dicom2json(input_filepath,
                   args.remove_dicom_fields)
    except Exception as error:
        raise error


if __name__ == "__main__":
    """
    Entry point of the script
    """
    try:
        main()
        exit(0)
    except ValueError as error:
        logger.exception(error)
        exit(1)
