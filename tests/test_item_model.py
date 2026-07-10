from typing import Any

import pytest
from bson.objectid import ObjectId
from girder.constants import AccessType
from girder.exceptions import GirderException

from bids_plugin.models import BIDSItemModel
from bids_plugin.utility import GirderModel


def check_bids_item_does_not_exist(dataset: GirderModel, folder: GirderModel, item_name: str) -> None:
    item_list = list(BIDSItemModel().find(query={"name": item_name, "dataset_id": dataset["_id"], "folderId": folder["_id"]}))
    assert len(item_list) == 0


def test_create_item(db: Any, dataset: GirderModel, datatype_folder: GirderModel, user: GirderModel) -> None:
    item_name = "sub-01_task-rest_analysis.nii.gz"
    created_item = BIDSItemModel().create_bids_item(
        user,
        item_name,
        dataset,
        datatype_folder,
    )

    assert created_item["name"] == item_name
    assert ObjectId(created_item["creatorId"]) == user["_id"]
    assert ObjectId(created_item["folderId"]) == datatype_folder["_id"]
    assert ObjectId(created_item.get("dataset_id")) == dataset["_id"]
    assert created_item.get("bids_hierarchy")
    assert "is_metadata" in created_item
    assert "source_id" in created_item

    saved_item = BIDSItemModel().load(created_item["_id"], user=user, level=AccessType.WRITE)

    assert saved_item


def test_create_item_in_folder_outside_dataset_raises_error(db: Any, folder: GirderModel, user: GirderModel) -> None:
    item_name = "sub-01_task-rest_analysis.nii.gz"
    with pytest.raises(GirderException) as exc_info:
        BIDSItemModel().create_bids_item(
            user,
            item_name,
            folder,
            folder,
        )

    assert "Invalid BIDS Dataset" in str(exc_info.value)

    check_bids_item_does_not_exist(folder, folder, item_name)


def test_create_item_in_folder_in_dataset_raises_error(
    db: Any, dataset: GirderModel, folder: GirderModel, user: GirderModel
) -> None:
    item_name = "sub-01_task-rest_analysis.nii.gz"
    with pytest.raises(GirderException) as exc_info:
        BIDSItemModel().create_bids_item(
            user,
            item_name,
            dataset,
            folder,
        )

    assert "Invalid BIDS Folder" in str(exc_info.value)

    check_bids_item_does_not_exist(dataset, folder, item_name)


def test_create_metadata_item_in_dataset(db: Any, dataset: GirderModel, user: GirderModel) -> None:
    item_name = "sub-01_task-rest_analysis.nii.gz"
    created_item = BIDSItemModel().create_bids_item(
        user,
        item_name,
        dataset,
        dataset,
        is_metadata=True,
    )

    assert created_item["name"] == item_name
    assert ObjectId(created_item["creatorId"]) == user["_id"]
    assert ObjectId(created_item["folderId"]) == dataset["_id"]
    assert ObjectId(created_item.get("dataset_id")) == dataset["_id"]
    assert created_item.get("bids_hierarchy")
    assert created_item.get("is_metadata")
    assert "source_id" in created_item

    saved_item = BIDSItemModel().load(created_item["_id"], user=user, level=AccessType.WRITE)

    assert saved_item


def test_create_data_item_in_dataset_raises_error(db: Any, dataset: GirderModel, user: GirderModel) -> None:
    item_name = "sub-01_task-rest_analysis.nii.gz"
    with pytest.raises(GirderException) as exc_info:
        BIDSItemModel().create_bids_item(
            user,
            item_name,
            dataset,
            dataset,
            is_metadata=False,
        )

    assert "Invalid BIDS Hierarchy" in str(exc_info.value)

    check_bids_item_does_not_exist(dataset, dataset, item_name)


def test_create_item_with_wrong_name_raises_error(
    db: Any, dataset: GirderModel, datatype_folder: GirderModel, user: GirderModel
) -> None:
    item_name = "analysis.nii.gz"
    with pytest.raises(GirderException) as exc_info:
        BIDSItemModel().create_bids_item(
            user,
            item_name,
            dataset,
            datatype_folder,
        )

    assert "Invalid BIDS Item name" in str(exc_info.value)

    check_bids_item_does_not_exist(dataset, datatype_folder, item_name)
