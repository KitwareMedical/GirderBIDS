import re
from datetime import datetime, timezone
from typing import Any

from girder import events
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.item import Item

from bids_plugin.models import BIDSDatasetModel, BIDSFolderModel
from bids_plugin.utility import BIDSDatatype, BIDSItem, GirderModel


class BIDSItemModel(Item):
    def initialize(self) -> None:
        super().initialize()
        self.exposeFields(
            level=AccessType.READ,
            fields=BIDSItem.fields(),
        )

    def _check_bids_hierarchy(
        self, item_name: GirderModel, item_extension: str | None, parent_folder: GirderModel
    ) -> None:
        parent_name = parent_folder["name"]
        if parent_name not in BIDSDatatype and not (
            item_extension is None or item_extension.startswith(("json", "tsv"))
        ):
            raise ValidationException("Invalid BIDS Hierarchy: data items must be at datatype level.")

        if "dataset_description" in parent_folder:
            return

        hierarchy = BIDSFolderModel().parents_to_dataset(parent_folder)
        prefix = "_".join(folder["name"] for folder in hierarchy)
        if not item_name.startswith(prefix):
            raise ValidationException(f"Invalid BIDS Item name: item name must start with '{prefix}'.")

    def _extract_bids_suffix_and_extension(self, item_name: str) -> tuple[str | None, str | None]:
        name_parts = item_name.split(".")
        base_name = name_parts[0]
        extension = ".".join(name_parts[1:]) if len(name_parts) > 1 else None

        if "-" not in base_name:
            return None, extension

        match = re.search(r"_([a-zA-Z0-9]+)$", base_name)
        if match:
            return match.group(1), extension

        return None, extension

    def parents_to_dataset(self, item: GirderModel, user: GirderModel | None = None) -> list[GirderModel]:
        force = user is None
        folder_model = BIDSFolderModel()
        parent_folder = folder_model.load(item["folderId"], level=AccessType.READ, user=user, force=force)
        return folder_model.parents_to_dataset(parent_folder, user, [folder_model.filter(parent_folder, user)])

    def create_bids_item(
        self,
        user: GirderModel,
        name: str,
        parent_folder: GirderModel,
        source: GirderModel | None = None,
        reuse_existing: bool = False,
    ) -> GirderModel | Any:
        if reuse_existing:
            existing = self.findOne({"folderId": parent_folder["_id"], "name": name})
            if existing:
                return existing

        if parent_folder.get("dataset_description"):
            BIDSDatasetModel().validate_bids(parent_folder)
            dataset_id = parent_folder["_id"]
        else:
            BIDSFolderModel().validate_bids(parent_folder)
            dataset_id = parent_folder["dataset_id"]

        suffix, extension = self._extract_bids_suffix_and_extension(name)

        self._check_bids_hierarchy(name, extension, parent_folder)

        item = self.createItem(name, user, parent_folder)
        item.update(
            BIDSItem(
                name=name,
                dataset_id=dataset_id,
                source_id=source["_id"] if source else None,
                suffix=suffix,
                extension=extension,
            ).as_dict()
        )

        return self.save_bids(item)

    def save_bids(self, item: GirderModel) -> GirderModel | Any:
        try:
            self.validate_bids(item)
            return self.save(item)
        except ValidationException as e:
            self.remove(item)
            raise e

    def validate_bids(self, item: GirderModel) -> None:
        if not item.get("dataset_id"):
            raise ValidationException("Invalid BIDS Item: missing 'dataset_id' field")

        if "source_id" not in item:
            raise ValidationException("Invalid BIDS Item: missing 'source_id' field")

        if "suffix" not in item:
            raise ValidationException("Invalid BIDS Item: missing 'suffix' field")

        if "extension" not in item:
            raise ValidationException("Invalid BIDS Item: missing 'extension' field")

    def set_bids_metadata(self, item: GirderModel, metadata: dict[str, Any]) -> GirderModel | Any:
        if "bids_metadata" not in item:
            item["bids_metadata"] = {}

        if item["extension"] == "json":
            # JSON files cannot have metadata
            return item

        # Add new metadata to existing metadata
        item["bids_metadata"].update(metadata.items())

        self.validateKeys(item["meta"])

        item["updated"] = datetime.now(timezone.utc)

        events.trigger("model.bids_item.bids_metadata.updated", item)

        return self.save_bids(item)
