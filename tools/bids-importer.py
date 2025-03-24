from enum import Enum
import fire
import girder_client
import json
import os
# from bids_validator import BIDSValidator
import subprocess
import sys

import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# logging.basicConfig(stream=sys.stdout)

# logging.getLogger().setLevel(logging.WARNING)
# logging.getLogger(__package__).setLevel(logging.DEBUG)

# def validate_bids(directory):
#     """Runs the BIDS Validator on the given directory."""
#     validator = BIDSValidator()
#     return validator.is_bids(directory)


def validate_bids(directory):
    """Runs the BIDS Validator on the given directory."""
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
    """Get or create a folder in Girder."""
    existing_folders = list(gc.listFolder(parent_id, name=folder_name))
    if existing_folders:
        return existing_folders[0]['_id']
    new_folder = gc.createFolder(parent_id, folder_name, parentType='folder')
    return new_folder['_id']


def delete_folder_contents(gc, folder_id):
    """Deletes all items and subfolders within a given folder."""
    # Delete all items in the folder
    for item in gc.listItem(folder_id):
        gc.delete(f"/item/{item['_id']}")  # Delete each item

    # Delete all subfolders
    for folder in gc.listFolder(folder_id):
        delete_folder_contents(gc, folder["_id"])  # Recursively delete contents
        gc.delete(f"/folder/{folder['_id']}")  # Delete the folder itself


def get_file_size(f): 
    f.seek(0, 2)  # Move to the end of the file
    file_size = f.tell()  # Get the position (size in bytes)
    f.seek(0, 0)  # Move back to the beginning of the file
    return file_size


def get_file_metadata(f):
    f.seek(0, 0)  # Move back to the beginning of the file
    return json.load(f)

class ImportMode(Enum):
    RESET_DATABASE = 'RESET_DATABASE'
    ERROR_ON_SAME_NAME = 'ERROR_ON_SAME_NAME'
    SKIP_ON_SAME_NAME = 'SKIP_ON_SAME_NAME'
    OVERWRITE_ON_SAME_NAME = 'OVERWRITE_ON_SAME_NAME'


def upload_to_girder(api_url, api_key, root_folder_id, bids_root,
                     import_mode):
    """Uploads valid BIDS files to Girder, preserving folder hierarchy."""
    gc = girder_client.GirderClient(apiUrl=api_url)
    gc.authenticate(apiKey=api_key)

    if import_mode == ImportMode.RESET_DATABASE.name:
        logger.info(f"Deleting folder {root_folder_id}")
        delete_folder_contents(gc, root_folder_id)

    for root, _, files in os.walk(bids_root):
        rel_path = os.path.relpath(root, bids_root)
        folders = rel_path.split(os.sep)
        parent_id = root_folder_id

        # Create folders in Girder
        for folder in folders:
            if folder != '.':
                parent_id = get_or_create_folder(gc, parent_id, folder)

        # Existing files
        existing_files = gc.listItem(parent_id)

        data_ids = {}
        files_metadata = {}

        # Upload files to the correct Girder folder
        for file in files:
            item = None
            for existing_file in existing_files:
                if existing_file["name"] == file:
                    item = existing_file
                    break

            file_path = os.path.join(root, file)

            if item is not None:
                if import_mode == ImportMode.ERROR_ON_SAME_NAME.name:
                    logger.error(f"File {file_path} already exists")
                    raise RuntimeError("File has already been imported")
                elif import_mode == ImportMode.SKIP_ON_SAME_NAME.name:
                    logger.debug(f"Skip existing file {file_path}")
                    continue
                elif import_mode == ImportMode.OVERWRITE_ON_SAME_NAME.name:
                    logger.debug(f"Overwrite existing file {file_path}")
            else:
                item = gc.createItem(parent_id, name=file, description="BIDS import")

            file_base, extension = os.path.splitext(file_path)
            if extension.lower() != '.json':
                data_ids[file_base] = item["_id"]

            logger.info(f"Uploading {file_path}...")
            with open(file_path, 'rb') as f:
                file_size = get_file_size(f)
                gc.uploadFile(item['_id'], f, size=file_size, name=file)

                if extension.lower() == '.json':
                    metadata = get_file_metadata(f)

                    if file == 'dataset_description.json':
                        gc.addMetadataToFolder(parent_id, metadata)
                    else:
                        files_metadata[file_base] = metadata

        # Upload files to the correct Girder folder
        for file_base, item in data_ids.items():
            if file_base in files_metadata:
                gc.addMetadataToItem(data_ids[file_base],
                                     files_metadata[file_base])

    logger.info("Upload complete!")


def main(bids_dir, girder_api_url, girder_api_key, girder_folder_id,
         import_mode: ImportMode = ImportMode.ERROR_ON_SAME_NAME):
    logger.info("Validating BIDS dataset is valid. Uploading to Girder...")
    if validate_bids(bids_dir):
        logger.info("BIDS dataset is valid. Uploading to Girder...")
        upload_to_girder(girder_api_url, girder_api_key, girder_folder_id,
                         bids_dir, import_mode)
    else:
        logger.error("BIDS dataset validation failed. Aborting upload.")
        sys.exit(1)


if __name__ == "__main__":
    fire.Fire(main)
