from typing import Any

import pytest
from bson.objectid import ObjectId
from girder.constants import AccessType
from girder.exceptions import ValidationException

from bids_plugin.models import BIDSDatasetModel
from bids_plugin.utility import BIDSDescription, GirderModel


def test_create_dataset_without_dataset_description_raises_error(
    db: Any, collection: GirderModel, user: GirderModel
) -> None:
    dataset_name = "Test Dataset"
    with pytest.raises(ValidationException) as exc_info:
        BIDSDatasetModel().create_bids_dataset(
            user,
            dataset_name,
            collection,
            BIDSDescription(),
            "collection",
        )

    assert "Invalid BIDS Dataset" in str(exc_info.value)

    saved_dataset = list(BIDSDatasetModel().find(query={"collection_id": collection["_id"], "name": dataset_name}))

    assert len(saved_dataset) == 0


def test_create_dataset_with_dataset_description(db: Any, collection: GirderModel, user: GirderModel) -> None:
    dataset_name = "Test Dataset"
    created_dataset = BIDSDatasetModel().create_bids_dataset(
        user,
        dataset_name,
        collection,
        parent_type="collection",
        dataset_description=BIDSDescription(Name=dataset_name, BIDSVersion="1.10.0"),
    )

    assert created_dataset["name"] == dataset_name
    assert ObjectId(created_dataset["creatorId"]) == user["_id"]
    assert created_dataset["baseParentId"] == collection["_id"]
    assert created_dataset.get("dataset_description")
    assert created_dataset.get("derivatives_folder_id")

    saved_dataset = BIDSDatasetModel().load(created_dataset["_id"], user=user, level=AccessType.WRITE)

    assert saved_dataset
