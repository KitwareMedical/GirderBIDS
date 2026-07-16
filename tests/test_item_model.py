from typing import Any

import pytest
from bson.objectid import ObjectId
from girder.constants import AccessType
from girder.exceptions import ValidationException

from bids_plugin.models import BIDSItemModel
from bids_plugin.utility import GirderModel


def check_bids_item_does_not_exist(folder: GirderModel, item_name: str) -> None:
    item_list = list(BIDSItemModel().find(query={"name": item_name, "folderId": folder["_id"]}))
    assert len(item_list) == 0


def test_create_item(db: Any, dataset: GirderModel, datatype_folder: GirderModel, user: GirderModel) -> None:
    item_name = "sub-01_task-rest_analysis.nii.gz"
    created_item = BIDSItemModel().create_bids_item(
        user,
        item_name,
        datatype_folder,
    )

    assert created_item["name"] == item_name
    assert ObjectId(created_item["creatorId"]) == user["_id"]
    assert ObjectId(created_item["folderId"]) == datatype_folder["_id"]
    assert ObjectId(created_item.get("dataset_id")) == dataset["_id"]
    assert "source_id" in created_item
    assert created_item["suffix"] == "analysis"
    assert created_item["extension"] == "nii.gz"

    saved_item = BIDSItemModel().load(created_item["_id"], user=user, level=AccessType.WRITE)

    assert saved_item


def test_create_item_in_folder_raises_error(db: Any, folder: GirderModel, user: GirderModel) -> None:
    item_name = "sub-01_task-rest_analysis.nii.gz"
    with pytest.raises(ValidationException) as exc_info:
        BIDSItemModel().create_bids_item(
            user,
            item_name,
            folder,
        )

    assert "Invalid BIDS Folder" in str(exc_info.value)

    check_bids_item_does_not_exist(folder, item_name)


def test_create_metadata_item_in_dataset(db: Any, dataset: GirderModel, user: GirderModel) -> None:
    item_name = "sub-01_task-rest_analysis.json"
    created_item = BIDSItemModel().create_bids_item(
        user,
        item_name,
        dataset,
    )

    assert created_item["name"] == item_name
    assert ObjectId(created_item["creatorId"]) == user["_id"]
    assert ObjectId(created_item["folderId"]) == dataset["_id"]
    assert ObjectId(created_item.get("dataset_id")) == dataset["_id"]
    assert "source_id" in created_item
    assert created_item["suffix"] == "analysis"
    assert created_item["extension"] == "json"

    saved_item = BIDSItemModel().load(created_item["_id"], user=user, level=AccessType.WRITE)

    assert saved_item


def test_create_data_item_in_dataset_raises_error(db: Any, dataset: GirderModel, user: GirderModel) -> None:
    item_name = "sub-01_task-rest_analysis.nii.gz"
    with pytest.raises(ValidationException) as exc_info:
        BIDSItemModel().create_bids_item(
            user,
            item_name,
            dataset,
            dataset,
        )

    assert "Invalid BIDS Hierarchy" in str(exc_info.value)

    check_bids_item_does_not_exist(dataset, item_name)


def test_create_item_with_wrong_name_raises_error(
    db: Any, dataset: GirderModel, datatype_folder: GirderModel, user: GirderModel
) -> None:
    item_name = "analysis.nii.gz"
    with pytest.raises(ValidationException) as exc_info:
        BIDSItemModel().create_bids_item(
            user,
            item_name,
            datatype_folder,
        )

    assert "Invalid BIDS Item name" in str(exc_info.value)

    check_bids_item_does_not_exist(datatype_folder, item_name)
