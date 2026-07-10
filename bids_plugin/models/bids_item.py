from typing import Any

from girder.constants import AccessType
from girder.exceptions import GirderException
from girder.models.item import Item

from bids_plugin.models import BIDSDatasetModel, BIDSFolderModel
from bids_plugin.utility import BIDSHierarchy, BIDSItem, GirderModel


class BIDSItemModel(Item):
    def initialize(self) -> None:
        super().initialize()
        self.exposeFields(
            level=AccessType.READ,
            fields=BIDSItem.fields(),
        )

    def _build_bids_hierarchy(self, doc: GirderModel, folder: GirderModel, is_metadata: bool) -> BIDSHierarchy:
        try:
            hierarchy = BIDSHierarchy(**folder["bids_hierarchy"])
            if hierarchy.datatype is None and not is_metadata:
                raise GirderException("Invalid BIDS Hierarchy: Data items must be at datatype level")
            name_parts = doc["name"].split(".")
            hierarchy.suffix = name_parts[0].split("_")[-1]
            hierarchy.ext = ".".join(name_parts[1:])
            return hierarchy

        except GirderException as e:
            self.remove(doc)
            raise e

    def create_bids_item(
        self,
        user: GirderModel,
        name: str,
        dataset: GirderModel,
        folder: GirderModel,
        source: GirderModel | None = None,
        is_metadata: bool = False,
    ) -> GirderModel | Any:
        BIDSDatasetModel().validate_bids(dataset)

        if folder["_id"] != dataset["_id"]:
            BIDSFolderModel().validate_bids(folder)

        bids_item = self.createItem(name, user, folder)
        hierarchy = self._build_bids_hierarchy(bids_item, folder, is_metadata)
        bids_item.update(
            BIDSItem(
                name=name,
                dataset_id=dataset["_id"],
                source_id=source["_id"] if source else None,
                bids_hierarchy=hierarchy,
                is_metadata=is_metadata,
            ).as_dict()
        )

        return self.save_bids(bids_item)

    def save_bids(self, doc: GirderModel) -> None:
        self.validate_bids(doc)
        return self.save(doc)

    def validate_bids(self, doc: GirderModel) -> None:
        try:
            if not doc.get("dataset_id"):
                raise GirderException("Invalid BIDS Item: missing 'dataset_id' field")

            if not doc.get("bids_hierarchy"):
                raise GirderException("Invalid BIDS Item: missing 'bids_hierarchy' field")

            if "source_id" not in doc:
                raise GirderException("Invalid BIDS Item: missing 'source_id' field")

            if "is_metadata" not in doc:
                raise GirderException("Invalid BIDS Item: missing 'is_metadata' field")

            item_name = doc["name"]
            if not doc["is_metadata"]:
                subject_name = doc["bids_hierarchy"]["subject"]
                session_name = doc["bids_hierarchy"]["session"]
                item_name_parts = item_name.split("_")
                if item_name_parts[0] != subject_name:
                    raise GirderException(f"Invalid BIDS Item name: item name must start with '{subject_name}'")

                if session_name is not None and item_name_parts[1] != session_name:
                    raise GirderException(
                        f"Invalid BIDS Item name: item name must start with '{subject_name}_{session_name}'"
                    )

                # NTH: could also check suffixes based on datatype

        except GirderException as e:
            self.remove(doc)
            raise e
