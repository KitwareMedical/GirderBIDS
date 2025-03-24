"""
BIDS Importer Script

This script validates and uploads BIDS (Brain Imaging Data Structure) datasets to a Girder instance.
It ensures proper validation using the BIDS Validator before uploading and preserves the folder
hierarchy while adding metadata.

Functions:
    - validate_bids(directory): Validates the BIDS dataset using bids-validator.
    - get_or_create_folder(gc, parent_id, folder_name): Retrieves or creates a folder in Girder.
    - delete_folder_contents(gc, folder_id): Deletes all items and subfolders within a given folder.
    - get_file_size(f): Retrieves the size of a file in bytes.
    - get_file_metadata(f): Extracts metadata from a JSON file.
    - get_file_path_metadata(file_path): Reads a JSON file and returns its contents as a dictionary.
    - is_bids_item(item): Determines whether a file is a BIDS metadata file.
    - get_associated_id(gc, parent_id, bids_item): Retrieves the associated ID for a BIDS item.
    - extract_bids_metadata(gc, folder_id, recursive): Extracts and assigns metadata to items in Girder.
    - upload_to_girder(api_url, api_key, root_folder_id, bids_root, import_mode): Uploads BIDS data to Girder.
    - main(bids_dir, girder_api_url, girder_api_key, girder_folder_id, import_mode, ignore_validation):
      Main function for validating and uploading BIDS data.

Classes:
    - ImportMode: Enum class defining different import modes.

:param bids_dir: Path to the BIDS dataset directory.
:param girder_api_url: The API URL of the Girder instance.
:param girder_api_key: API key for authentication with Girder.
:param girder_folder_id: The ID of the root folder in Girder where the data will be uploaded.
:param import_mode: The mode for handling existing data in Girder (default: OVERWRITE_ON_SAME_NAME).
:param ignore_validation: Whether to skip BIDS validation before upload (default: False).

Usage:
    python bids-importer.py --bids_dir <path> --girder_api_url <url> --girder_api_key <key> --girder_folder_id <id> 
                            --import_mode <mode> --ignore_validation <True/False>
"""

from enum import Enum
import fire
import girder_client
import io
import json
import os
# from bids_validator import BIDSValidator
import subprocess
import sys

import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)


def validate_bids(directory):
    """
    Runs the BIDS Validator on the given directory.

    :param directory: Path to the BIDS dataset directory.
    :return: Boolean indicating whether the dataset is valid.
    """
    try:
        result = subprocess.run(['bids-validator', '--json', directory],
                                capture_output=True, text=True)
        output = result.stdout
        errors = result.stderr
        if errors:
            logger.error(f"Validation errors: {errors}")
            return False
        # Check if there are no errors
        return ('"errors": []' in output or
                '"severity": "error"' not in output)
    except FileNotFoundError:
        logger.error("bids-validator not found. Make sure you installed bids-validator-deno")
        return False


def get_or_create_folder(gc, parent_id, folder_name):
    """
    Retrieves or creates a folder in Girder.

    :param gc: Girder client instance.
    :param parent_id: ID of the parent folder.
    :param folder_name: Name of the folder to retrieve or create.
    :return: Folder ID.
    """
    existing_folders = list(gc.listFolder(parent_id, name=folder_name))
    if existing_folders:
        return existing_folders[0]['_id']
    new_folder = gc.createFolder(parent_id, folder_name, parentType='folder')
    return new_folder['_id']


def delete_folder_contents(gc, folder_id):
    """
    Deletes all items and subfolders within a given folder.

    :param gc: Girder client instance.
    :param folder_id: ID of the folder to clear.
    """
    # Delete all items in the folder
    for item in gc.listItem(folder_id):
        gc.delete(f"/item/{item['_id']}")  # Delete each item

    # Delete all subfolders
    for folder in gc.listFolder(folder_id):
        delete_folder_contents(gc, folder["_id"])  # Recursively delete contents
        gc.delete(f"/folder/{folder['_id']}")  # Delete the folder itself


def get_file_size(f):
    """
    Retrieves the size of a file in bytes.
    
    :param f: File object.
    :return: Size of the file in bytes.
    """
    f.seek(0, 2)  # Move to the end of the file
    file_size = f.tell()  # Get the position (size in bytes)
    f.seek(0, 0)  # Move back to the beginning of the file
    return file_size


def get_file_metadata(f):
    """Convert a file object that contains a JSON file into a dictionnary"""
    f.seek(0, 0)
    return json.load(f)


def get_file_path_metadata(file_path):
    """
    Reads a JSON file and returns its contents as a dictionary.

    :param file_path: Path to the JSON file.
    :return: Dictionary containing the file's metadata.
    """
    with open(file_path, 'rb') as f:
        return get_file_metadata(f)


def is_bids_item(item):
    """
    Determines whether a given file is a BIDS metadata file.

    :param item: The item (file) to check.
    :return: True if the item is a BIDS metadata file, False otherwise.
    """
    return item['name'].endswith('.json')


def get_associated_id(gc, parent_id, bids_item):
    """
    Retrieves the associated ID for a BIDS item.

    :param gc: Girder client instance.
    :param parent_id: ID of the parent folder in Girder.
    :param bids_item: The BIDS item to find an associated ID for.
    :return: A tuple containing the associated ID and its type (folder or item), or None if not found.
    """
    file_name = bids_item['name']
    if file_name == 'dataset_description.json':
        return parent_id, 'folder'
    file_base, extension = os.path.splitext(file_name)
    for item in gc.listItem(parent_id):
        if item['name'].startswith(file_base):
            return item['_id'], 'item'
    return None


class ImportMode(Enum):
    """
    Enum class defining different import modes for handling existing data in Girder.

    :param RESET_DATABASE: Deletes all existing data before uploading new data.
    :param OVERWRITE_ON_SAME_NAME: Overwrites existing datasets with the same name.
    """
    RESET_DATABASE = 'RESET_DATABASE'
    OVERWRITE_ON_SAME_NAME = 'OVERWRITE_ON_SAME_NAME'


def extract_bids_metadata(gc, folder_id, recursive=True):
    """
    Extracts metadata from BIDS-related JSON files and adds it to Girder.

    :param gc: Girder client instance.
    :param folder_id: ID of the Girder folder containing BIDS data.
    :param recursive: Whether to process subfolders recursively (default: True).
    """
    for item in gc.listItem(folder_id):
        if is_bids_item(item):
            associated_id, type = get_associated_id(gc, folder_id, item)
            bids_file = next(gc.listFile(item['_id'], limit=1))
            file_obj = io.BytesIO()
            for chunk in gc.downloadFileAsIterator(bids_file['_id']):
                if chunk:
                    file_obj.write(chunk)
            metadata = get_file_metadata(file_obj)
            if type == 'item':
                gc.addMetadataToItem(associated_id, metadata)
            elif type == 'folder':
                gc.addMetadataToFolder(associated_id, metadata)

    if recursive:
        for child_folder_id in gc.listFolder(folder_id):
            extract_bids_metadata(gc, child_folder_id['_id'])


def upload_to_girder(api_url, api_key, root_folder_id, bids_root,
                     import_mode):
    """
    Uploads valid BIDS files to Girder, preserving folder hierarchy.

    :param api_url: Girder API URL.
    :param api_key: API key for authentication.
    :param root_folder_id: ID of the root folder in Girder where files will be uploaded.
    :param bids_root: Root directory of the BIDS dataset.
    :param import_mode: Mode for handling existing data.
    """
    gc = girder_client.GirderClient(apiUrl=api_url)
    gc.authenticate(apiKey=api_key)

    if import_mode == ImportMode.RESET_DATABASE.name:
        logger.info(f"Deleting folder {root_folder_id}")
        delete_folder_contents(gc, root_folder_id)

    gc.upload(bids_root, root_folder_id, 'folder', leafFoldersAsItems=False,
              reuseExisting=True)
    extract_bids_metadata(gc, root_folder_id)

    logger.info("Upload complete!")


def main(bids_dir, girder_api_url, girder_api_key, girder_folder_id,
         import_mode: ImportMode = ImportMode.OVERWRITE_ON_SAME_NAME,
         ignore_validation: bool = False):
    """
    Main function for validating and uploading BIDS datasets.

    :param bids_dir: Path to the BIDS dataset directory.
    :param girder_api_url: The API URL of the Girder instance.
    :param girder_api_key: API key for authentication.
    :param girder_folder_id: The ID of the root folder in Girder where the data will be uploaded.
    :param import_mode: The mode for handling existing data in Girder.
    :param ignore_validation: Whether to skip BIDS validation before upload.
    """
    if not ignore_validation:
        logger.info("Validating BIDS dataset...")
        if validate_bids(bids_dir):    
            logger.info("BIDS dataset is valid")
        else:
            logger.error("BIDS dataset validation failed. Aborting upload.")
            sys.exit(1)
    logger.info("Uploading to Girder...")
    upload_to_girder(girder_api_url, girder_api_key, girder_folder_id,
                     bids_dir, import_mode)


if __name__ == "__main__":
    fire.Fire(main)
