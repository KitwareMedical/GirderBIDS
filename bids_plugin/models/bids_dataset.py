from typing import Any

from girder.constants import AccessType
from girder.exceptions import GirderException
from girder.models.folder import Folder

from bids_plugin.utility import (
    BIDSDataset,
    BIDSDescription,
    BIDSHierarchy,
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
    ) -> GirderModel | Any:
        bids_dataset_folder = self.createFolder(parent, name, parentType=parent_type, creator=user, allowRename=True)

        bids_hierarchy = BIDSHierarchy()

        if dataset_description.DatasetType == "raw":
            derivatives_folder_id = self.createFolder(bids_dataset_folder, name="derivatives")["_id"]
        else:
            derivatives_folder_id = None
            bids_hierarchy.is_derivative = True

        bids_dataset = BIDSDataset(
            name=name,
            dataset_description=dataset_description,
            derivatives_folder_id=derivatives_folder_id,
            bids_hierarchy=bids_hierarchy,
        ).as_dict()

        bids_dataset_folder.update(bids_dataset)
        return self.save_bids(bids_dataset_folder)

    def save_bids(self, doc: GirderModel) -> None:
        self.validate_bids(doc)
        return self.save(doc)

    def validate_bids(self, doc: GirderModel) -> None:
        try:
            if "dataset_description" not in doc:
                raise GirderException("Invalid BIDS Dataset: missing 'dataset_description' field")

            if "derivatives_folder_id" not in doc:
                raise GirderException("Invalid BIDS Dataset: missing 'derivatives_folder_id' field")

            if "bids_hierarchy" not in doc:
                raise GirderException("Invalid BIDS Dataset: missing 'bids_hierarchy' field")

            if not doc["dataset_description"].get("BIDSVersion"):
                raise GirderException("Invalid BIDS Dataset: missing 'BIDSVersion' field in dataset description")

        except GirderException as e:
            self.remove(doc)
            raise e
