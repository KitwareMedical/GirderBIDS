from typing import Any

from girder.constants import AccessType
from girder.exceptions import GirderException
from girder.models.folder import Folder
from pymongo.cursor import Cursor

from bids_plugin.models import BIDSDatasetModel
from bids_plugin.utility import (
    BIDSDatatype,
    BIDSFolder,
    BIDSHierarchy,
    GirderModel,
    MongoOperators,
)


class BIDSFolderModel(Folder):
    def initialize(self) -> None:
        super().initialize()
        self.exposeFields(
            level=AccessType.READ,
            fields=BIDSFolder.fields(),
        )

    def _build_folder_hierarchy(self, doc: GirderModel, folder: GirderModel) -> BIDSHierarchy:
        try:
            hierarchy = BIDSHierarchy(**folder["bids_hierarchy"])
            if doc["name"].startswith("sub-"):
                if hierarchy.subject is not None:
                    raise GirderException("Invalid BIDS Hierarchy: Subject folder must be at dataset level.")
                hierarchy.subject = doc["name"]
                return hierarchy

            if doc["name"].startswith("ses-"):
                if hierarchy.subject is None or hierarchy.session is not None:
                    raise GirderException("Invalid BIDS Hierarchy: Session folder must be at subject level.")
                hierarchy.session = doc["name"]
                return hierarchy

            if doc["name"] in BIDSDatatype:
                if hierarchy.subject is None:
                    raise GirderException(
                        "Invalid BIDS Hierarchy: Datatype folder must be at subject or session level."
                    )
                hierarchy.datatype = doc["name"]
                return hierarchy

            raise GirderException("Invalid BIDS Folder name: Unconventional BIDS folder name")

        except GirderException as e:
            self.remove(doc)
            raise e

    def create_bids_folder(
        self,
        user: GirderModel,
        name: str,
        dataset: GirderModel,
        folder: GirderModel,
    ) -> GirderModel | Any:
        BIDSDatasetModel().validate_bids(dataset)
        if folder["_id"] != dataset["_id"]:
            self.validate_bids(folder)

        bids_folder = self.createFolder(folder, name, creator=user)
        bids_hierarchy = self._build_folder_hierarchy(bids_folder, folder)
        bids_folder.update(
            BIDSFolder(
                name=name,
                dataset_id=dataset["_id"],
                bids_hierarchy=bids_hierarchy,
            ).as_dict()
        )

        return self.save_bids(bids_folder)

    def save_bids(self, doc: GirderModel) -> None:
        self.validate_bids(doc)
        return self.save(doc)

    def validate_bids(self, doc: GirderModel) -> None:
        try:
            if not doc.get("dataset_id"):
                raise GirderException("Invalid BIDS Folder: missing 'dataset_id' field")

            if not doc.get("bids_hierarchy"):
                raise GirderException("Invalid BIDS Folder: missing 'bids_hierarchy' field")

        except GirderException as e:
            self.remove(doc)
            raise e
