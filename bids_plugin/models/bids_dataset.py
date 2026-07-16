from typing import Any

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.folder import Folder

from bids_plugin.utility import (
    BIDSDataset,
    BIDSDescription,
    GirderModel,
)


class BIDSDatasetModel(Folder):
    def initialize(self) -> None:
        super().initialize()
        self.exposeFields(
            level=AccessType.READ,
            fields=BIDSDataset.fields(),
        )

    def create_bids_dataset(
        self,
        user: GirderModel,
        name: str,
        parent: GirderModel,
        dataset_description: BIDSDescription,
        parent_type: str = "folder",
        reuse_existing: bool = False,
    ) -> GirderModel | Any:
        if reuse_existing:
            name.strip("")
            existing = self.findOne({"parentId": parent["_id"], "name": name})
            if existing:
                return existing

        bids_dataset_folder = self.createFolder(parent, name, parentType=parent_type, creator=user, allowRename=True)

        if dataset_description.DatasetType == "raw":
            derivatives_folder_id = self.createFolder(bids_dataset_folder, name="derivatives")["_id"]
        else:
            derivatives_folder_id = None

        bids_dataset = BIDSDataset(
            name=name,
            dataset_description=dataset_description,
            derivatives_folder_id=derivatives_folder_id,
        ).as_dict()

        bids_dataset_folder.update(bids_dataset)
        return self.save_bids(bids_dataset_folder)

    def save_bids(self, dataset: GirderModel) -> None:
        try:
            self.validate_bids(dataset)
            return self.save(dataset)

        except ValidationException as e:
            self.remove(dataset)
            raise e

    def validate_bids(self, dataset: GirderModel) -> None:
        if "dataset_description" not in dataset:
            raise ValidationException("Invalid BIDS Dataset: missing 'dataset_description' field")

        if "derivatives_folder_id" not in dataset:
            raise ValidationException("Invalid BIDS Dataset: missing 'derivatives_folder_id' field")

        if not dataset["dataset_description"].get("BIDSVersion"):
            raise ValidationException("Invalid BIDS Dataset: missing 'BIDSVersion' field in dataset description")
