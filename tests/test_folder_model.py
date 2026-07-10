from typing import Any

import pytest
from bson.objectid import ObjectId
from girder.constants import AccessType
from girder.exceptions import GirderException

from bids_plugin.models import BIDSFolderModel
from bids_plugin.utility import GirderModel


def check_bids_folder_does_not_exist(dataset: GirderModel, folder_name: str) -> None:
    folder_list = list(BIDSFolderModel().find(query={"dataset_id": dataset["_id"], "name": folder_name}))
    assert len(folder_list) == 0


def test_create_subject_folder_in_dataset(db: Any, dataset: GirderModel, user: GirderModel) -> None:
    subject_folder_name = "sub-01"
    created_subject_folder = BIDSFolderModel().create_bids_folder(
        user,
        subject_folder_name,
        dataset,
        dataset,
    )

    assert created_subject_folder["name"] == subject_folder_name
    assert ObjectId(created_subject_folder["creatorId"]) == user["_id"]
    assert ObjectId(created_subject_folder["parentId"]) == dataset["_id"]
    assert ObjectId(created_subject_folder.get("dataset_id")) == dataset["_id"]
    assert created_subject_folder.get("bids_hierarchy")
    assert created_subject_folder["bids_hierarchy"].get("subject") == subject_folder_name

    saved_subject = BIDSFolderModel().load(created_subject_folder["_id"], user=user, level=AccessType.WRITE)

    assert saved_subject


def test_create_subject_in_folder_outside_dataset_raises_error(db: Any, folder: GirderModel, user: GirderModel) -> None:
    subject_folder_name = "sub-01"
    with pytest.raises(GirderException) as exc_info:
        BIDSFolderModel().create_bids_folder(
            user,
            subject_folder_name,
            folder,
            folder,
        )

    assert "Invalid BIDS Dataset" in str(exc_info.value)

    check_bids_folder_does_not_exist(folder, subject_folder_name)


def test_create_subject_in_folder_in_dataset_raises_error(
    db: Any, dataset: GirderModel, folder: GirderModel, user: GirderModel
) -> None:
    subject_folder_name = "sub-01"
    with pytest.raises(GirderException) as exc_info:
        BIDSFolderModel().create_bids_folder(
            user,
            subject_folder_name,
            dataset,
            folder,
        )

    assert "Invalid BIDS Folder" in str(exc_info.value)

    check_bids_folder_does_not_exist(dataset, subject_folder_name)


def test_create_subject_with_wrong_name_raises_error(db: Any, dataset: GirderModel, user: GirderModel) -> None:
    subject_folder_name = "subject1"
    with pytest.raises(GirderException) as exc_info:
        BIDSFolderModel().create_bids_folder(
            user,
            subject_folder_name,
            dataset,
            dataset,
        )

    assert "Invalid BIDS Folder name" in str(exc_info.value)

    check_bids_folder_does_not_exist(dataset, subject_folder_name)


def test_create_session_in_dataset_raises_error(db: Any, dataset: GirderModel, user: GirderModel) -> None:
    session_name = "ses-01"
    with pytest.raises(GirderException) as exc_info:
        BIDSFolderModel().create_bids_folder(
            user,
            session_name,
            dataset,
            dataset,
        )

    assert "Invalid BIDS Hierarchy" in str(exc_info.value)

    check_bids_folder_does_not_exist(dataset, session_name)
