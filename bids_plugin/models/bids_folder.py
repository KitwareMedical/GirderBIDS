from typing import Any

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.folder import Folder

from bids_plugin.models import BIDSDatasetModel
from bids_plugin.utility import (
    BIDSDatatype,
    BIDSFolder,
    GirderModel,
)


class BIDSFolderModel(Folder):
    def initialize(self) -> None:
        super().initialize()
        self.exposeFields(
            level=AccessType.READ,
            fields=BIDSFolder.fields(),
        )

    def _check_bids_hierarchy(self, folder_name: GirderModel, parent_folder: GirderModel) -> None:
        parent_name = parent_folder["name"]
        if folder_name.startswith("sub-"):
            if parent_name.startswith("sub-"):
                raise ValidationException("Invalid BIDS Hierarchy: Subject folder must be at dataset level.")
            return

        if folder_name.startswith("ses-"):
            if not parent_name.startswith("sub-"):
                raise ValidationException("Invalid BIDS Hierarchy: Session folder must be at subject level.")
            return

        if BIDSDatatype.has_datatype(folder_name):
            if not parent_name.startswith(("sub-", "ses-")):
                raise ValidationException(
                    "Invalid BIDS Hierarchy: Datatype folder must be at subject or session level."
                )
            return

        raise ValidationException("Invalid BIDS Folder name: Unconventional BIDS folder name")

    def parents_to_dataset(
        self, folder: GirderModel, user: GirderModel | None = None, path: list[GirderModel] | None = None
    ) -> list[GirderModel]:
        force = user is None
        path = path or []
        parent_id = folder["parentId"]
        if parent_id == folder["dataset_id"]:
            return path

        parent_folder = self.load(parent_id, level=AccessType.READ, user=user, force=force)
        path = [self.filter(parent_folder, user), *path]
        return self.parents_to_dataset(parent_folder, user, path)

    def create_bids_folder(
        self,
        user: GirderModel,
        name: str,
        parent_folder: GirderModel,
        reuse_existing: bool = False,
    ) -> GirderModel | Any:
        if reuse_existing:
            existing = self.findOne({"parentId": parent_folder["_id"], "name": name})
            if existing:
                return existing

        if parent_folder.get("dataset_description"):
            BIDSDatasetModel().validate_bids(parent_folder)
            dataset_id = parent_folder["_id"]
        else:
            BIDSFolderModel().validate_bids(parent_folder)
            dataset_id = parent_folder["dataset_id"]

        self._check_bids_hierarchy(name, parent_folder)

        bids_folder = self.createFolder(parent_folder, name, creator=user)
        bids_folder.update(
            BIDSFolder(
                name=name,
                dataset_id=dataset_id,
            ).as_dict()
        )

        return self.save_bids(bids_folder)

    def save_bids(self, folder: GirderModel) -> None:
        try:
            self.validate_bids(folder)
            return self.save(folder)

        except ValidationException as e:
            self.remove(folder)
            raise e

    def validate_bids(self, folder: GirderModel) -> None:
        if not folder.get("dataset_id"):
            raise ValidationException("Invalid BIDS Folder: missing 'dataset_id' field")
