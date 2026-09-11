import io
import json
import logging
import subprocess
import sys
from pathlib import Path

import fire
import girder_client

from bids_plugin.utility.models import GirderModel

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


BIDS_COMPOUND_EXTENSIONS = {
    ".nii.gz",
    ".tsv.gz",
}


def bids_stem(filename: str) -> str:
    """Return the filename without its BIDS extension."""
    name = Path(filename).name

    for ext in BIDS_COMPOUND_EXTENSIONS:
        if name.endswith(ext):
            return name[: -len(ext)]

    return Path(name).stem


def validate_bids(directory: str) -> bool:
    """
    Runs the BIDS Validator on the given directory.

    :param directory: Path to the BIDS dataset directory.
    :return: Boolean indicating whether the dataset is valid.
    """
    try:
        result = subprocess.run(
            ["bids-validator-deno", "--json", directory], check=False, capture_output=True, text=True
        )
        output = result.stdout
        errors = result.stderr
        if errors:
            logger.error(f"Validation errors: {errors}")
            return False
        # Check if there are no errors
        return '"errors": []' in output or '"severity": "error"' not in output
    except FileNotFoundError:
        logger.error("bids-validator not found. Make sure you installed bids-validator-deno")
        return False


class BIDSImporter:
    def __init__(self, bids_dir: str, api_url: str, api_key: str, location_id: str, location_type: str) -> None:
        """
        :param bids_dir: Path to the BIDS dataset directory.
        :param api_url: The API URL of the Girder instance.
        :param api_key: API key for authentication.
        :param location_id: The ID of the root folder in Girder where the data will be uploaded.
        :param location_type: The type of the root folder: "folder" or "collection".
        """
        self.bids_dir = Path(bids_dir)
        self.root_folder_id = location_id
        self.root_folder_type = location_type
        self.dataset_name = self.bids_dir.resolve().name

        self.girder_client = girder_client.GirderClient(apiUrl=api_url)
        self.girder_client.authenticate(apiKey=api_key)

    def _get_item_metadata(self, item: GirderModel) -> str:
        """Extract metadata from item files"""
        metadata_file = next(self.girder_client.listFile(item["_id"], limit=1))
        file_obj = io.BytesIO()
        for chunk in self.girder_client.downloadFileAsIterator(metadata_file["_id"]):
            if chunk:
                file_obj.write(chunk)
        file_obj.seek(0, 0)
        return json.load(file_obj)

    def _get_associated_item(self, folder_id: str, metadata_item: GirderModel) -> GirderModel | None:
        """
        Retrieves the data item associated to a metadata item.

        :param folder_id: ID of the parent folder in Girder.
        :param item: The BIDS item to find an associated ID for.
        :return: A tuple containing the associated ID and its type (folder or item), or None if not found.
        """
        file_name = bids_stem(metadata_item["name"])
        for item in self.girder_client.listItem(folder_id):
            if item["_id"] == metadata_item["_id"]:
                continue

            if item["name"].startswith(file_name):
                return item
        return None

    def _extract_metadata(self, use_plugin: bool, location_id: str, location_type: str = "folder") -> None:
        """
        Extracts metadata from JSON files and adds it to Girder item's metadata.

        :param folder_id: ID of the Girder folder containing BIDS data.
        """
        if location_type == "folder":
            for item in self.girder_client.listItem(location_id):
                if item["name"] == "dataset_description.json":
                    if use_plugin:
                        # with the plugin dataset_description is already in the dataset_description field of the model
                        continue

                    dataset_desc = self._get_item_metadata(item)
                    self.girder_client.addMetadataToFolder(location_id, dataset_desc)

                elif item["name"].endswith(".json"):
                    associated_item = self._get_associated_item(location_id, item)
                    if associated_item is None:
                        continue

                    metadata = self._get_item_metadata(item)
                    if use_plugin:
                        self.girder_client.put(f"bids_item/{associated_item['_id']}/metadata", json=metadata)
                    else:
                        self.girder_client.addMetadataToItem(associated_item["_id"], metadata)

        for child_folder_id in self.girder_client.listFolder(location_id, location_type):
            self._extract_metadata(use_plugin, child_folder_id["_id"])

    def extract_metadata(self, use_plugin: bool = False) -> None:
        self._extract_metadata(use_plugin, self.root_folder_id, self.root_folder_type)

    def upload_dataset(self, use_plugin: bool = False) -> None:
        if len(list(self.girder_client.listFolder(self.root_folder_id, self.root_folder_type, self.dataset_name))) > 0:
            raise Exception(f"A folder named {self.dataset_name} already exists in the Girder database")

        if use_plugin:
            self._plugin_upload_dataset(self.bids_dir, self.root_folder_id, self.root_folder_type)
        else:
            self.girder_client.upload(
                str(self.bids_dir), self.root_folder_id, self.root_folder_type, leafFoldersAsItems=False
            )

    def _plugin_upload_dataset(self, file_pattern: Path, parent_id: str, parent_type: str = "folder") -> None:
        logger.info(f"Creating BIDS Dataset from {file_pattern.name}")
        # Create dataset
        dataset_desc_file = file_pattern / "dataset_description.json"
        with dataset_desc_file.open("r") as f:
            dataset_desc = f.read()

        dataset_folder = self.girder_client.post(
            "bids_dataset",
            parameters={
                "name": file_pattern.name,
                "parent_id": parent_id,
                "parent_type": parent_type,
                "dataset_description": dataset_desc,
            },
        )

        # Parse dataset recursively
        for element_path in file_pattern.iterdir():
            if element_path.is_file():
                self._plugin_upload_item(element_path, dataset_folder["_id"])

            elif element_path.name == "derivatives":
                derivative_folder = self.girder_client.loadOrCreateFolder(
                    element_path.name, dataset_folder["_id"], "folder"
                )
                for derivative_element_path in element_path.iterdir():
                    if derivative_element_path.is_dir():
                        self._plugin_upload_dataset(derivative_element_path, derivative_folder["_id"])

            else:
                self._plugin_upload_folder(element_path, dataset_folder["_id"])

    def _plugin_upload_folder(self, folder_path: Path, parent_id: str) -> None:
        logger.info(f"Creating BIDS Folder from {folder_path.name}")
        folder = self.girder_client.post(
            "bids_folder",
            parameters={
                "folder_id": parent_id,
                "name": folder_path.name,
            },
        )

        for element_path in folder_path.iterdir():
            if element_path.is_dir():
                self._plugin_upload_folder(element_path, folder["_id"])
            else:
                self._plugin_upload_item(
                    element_path,
                    folder["_id"],
                )

    def _plugin_upload_item(self, item_path: Path, folder_id: str) -> None:
        logger.info(f"Creating BIDS Item from {item_path.name}")
        item = self.girder_client.post(
            "bids_item",
            parameters={
                "folder_id": folder_id,
                "name": item_path.name,
            },
        )
        self.girder_client.uploadFileToItem(item["_id"], str(item_path))

    def clean(self) -> None:
        dataset_folder = next(
            self.girder_client.listFolder(self.root_folder_id, self.root_folder_type, self.dataset_name), None
        )
        if dataset_folder:
            self.girder_client.delete(
                "resource", parameters={"resources": json.dumps({"folder": [dataset_folder["_id"]]})}
            )
            logger.warning(f"{self.dataset_name} deleted from database after failed/partial import")


def main(
    bids_dir: str,
    api_url: str,
    api_key: str,
    location_id: str,
    location_type: str = "folder",
    ignore_validation: bool = False,
    use_plugin: bool = False,
    extract_metadata: bool = False,
) -> None:
    """
    Main function for validating and uploading BIDS datasets.

    :param bids_dir: Path to the BIDS dataset directory.
    :param api_url: The API URL of the Girder instance.
    :param api_key: API key for authentication.
    :param location_id: The ID of the root folder in Girder where the data will be uploaded.
    :param location_type: The type of the root folder: "folder" or "collection".
    :param ignore_validation: Whether to skip BIDS validation before upload.
    :param use_plugin: whether to use BIDS Girder plugin
    :param extract_metadata: whether to extract metadata of files to enrich items metadata
    """
    if not ignore_validation:
        logger.info("Validating BIDS dataset...")
        if validate_bids(bids_dir):
            logger.info("BIDS dataset is valid")
        else:
            logger.error("BIDS dataset validation failed. Aborting upload.")
            sys.exit(1)
    logger.info("Uploading to Girder...")

    importer = BIDSImporter(bids_dir, api_url, api_key, location_id, location_type)

    try:
        logger.debug("Upload dataset")
        importer.upload_dataset(use_plugin)
    except girder_client.HttpError as e:
        logger.error(f"Could not upload dataset: {e}")
        importer.clean()
    else:
        if extract_metadata:
            logger.debug("Extract metadata")
            importer.extract_metadata(use_plugin)
        logger.info("Successful upload of dataset")


def cli() -> None:
    fire.Fire(main)


if __name__ == "__main__":
    cli()
