from typing import Any

import pytest
from girder.constants import AccessType
from girder.models.collection import Collection

from bids_plugin.models import BIDSDatasetModel, BIDSFolderModel, BIDSItemModel
from bids_plugin.utility import BIDSDataset, BIDSDescription


def pytest_collection_modifyitems(items: Any) -> None:
    for item in items:
        item.add_marker(pytest.mark.plugin("bids_plugin"))


@pytest.fixture
def collection(user: Any) -> Any:
    return Collection().createCollection("Test collection", creator=user)


@pytest.fixture
def folder(collection: Any, user: Any) -> Any:
    return BIDSFolderModel().createFolder(collection, "Random folder", parentType="collection")


@pytest.fixture
def raw_dataset_description() -> Any:
    return BIDSDescription(BIDSVersion="1.8.0")


@pytest.fixture
def derivative_dataset_description() -> Any:
    return BIDSDescription(BIDSVersion="1.8.0", DatasetType="derivative")


@pytest.fixture
def derivative_dataset(dataset: BIDSDataset, user: Any, derivative_dataset_description: Any) -> Any:
    derivatives_folder = BIDSFolderModel.load(dataset["derivatives_folder_id"], AccessType.WRITE, user)
    return BIDSDatasetModel().create_bids_dataset(
        user, "Derivative Dataset", parent=derivatives_folder, dataset_description=derivative_dataset_description
    )


@pytest.fixture
def dataset(collection: Any, user: Any, raw_dataset_description: Any) -> Any:
    return BIDSDatasetModel().create_bids_dataset(
        user, "Dataset 1", parent=collection, parent_type="collection", dataset_description=raw_dataset_description
    )


@pytest.fixture
def subject_folder(dataset: Any, user: Any) -> Any:
    return BIDSFolderModel().create_bids_folder(
        user,
        "sub-01",
        dataset,
    )


@pytest.fixture
def datatype_folder(subject_folder: Any, user: Any) -> Any:
    return BIDSFolderModel().create_bids_folder(
        user,
        "anat",
        subject_folder,
    )


@pytest.fixture
def dataset_list(
    collection: Any, user: Any, raw_dataset_description: Any, derivative_dataset_description: Any
) -> list[Any]:
    dataset1 = BIDSDatasetModel().create_bids_dataset(
        user, "Dataset 1", collection, raw_dataset_description, "collection"
    )
    dataset2 = BIDSDatasetModel().create_bids_dataset(
        user, "Dataset 2", collection, raw_dataset_description, "collection"
    )
    dataset3 = BIDSDatasetModel().create_bids_dataset(
        user, "Dataset 3", collection, derivative_dataset_description, "collection"
    )
    return [dataset1, dataset2, dataset3]


@pytest.fixture
def subject_folder_list(dataset: Any, user: Any) -> Any:
    return [BIDSFolderModel().create_bids_folder(user, f"sub-0{i + 1}", dataset) for i in range(2)]


@pytest.fixture
def item_list(datatype_folder: Any, user: Any) -> Any:
    return [
        BIDSItemModel().create_bids_item(user, f"sub-01_task-rest_analysis{i + 1}.nii.gz", datatype_folder)
        for i in range(2)
    ]
