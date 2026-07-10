from typing import Any

from bson.objectid import ObjectId
from girder.constants import AccessType
from pytest_girder.assertions import assertStatusOk

from bids_plugin.models import BIDSFolderModel
from bids_plugin.utility import GirderModel


def test_list_folders(
    db: Any, dataset: GirderModel, subject_folder_list: list[GirderModel], server: Any, user: Any
) -> None:
    resp = server.request(
        method="GET",
        path="/bids_folder",
        params={"dataset_id": dataset["_id"]},
        user=user,
    )

    assertStatusOk(resp)

    resp_subject_folder_list = resp.json

    assert len(resp_subject_folder_list) == 2
    assert any(ds["name"] == subject_folder_list[0]["name"] for ds in resp_subject_folder_list)
    assert any(ds["name"] == subject_folder_list[1]["name"] for ds in resp_subject_folder_list)


def test_create_subject_folder(db: Any, dataset: GirderModel, server: Any, user: GirderModel) -> None:
    subject_folder_name = "sub-01"
    resp = server.request(
        method="POST",
        path="/bids_folder",
        params={
            "dataset_id": dataset["_id"],
            "folder_id": dataset["_id"],
            "name": subject_folder_name,
        },
        user=user,
    )
    resp_subject_folder = resp.json

    assertStatusOk(resp)
    assert resp_subject_folder["name"] == subject_folder_name
    assert ObjectId(resp_subject_folder["creatorId"]) == user["_id"]
    assert ObjectId(resp_subject_folder["parentId"]) == dataset["_id"]
    assert ObjectId(resp_subject_folder.get("dataset_id")) == dataset["_id"]
    assert resp_subject_folder.get("bids_hierarchy")
    assert resp_subject_folder["bids_hierarchy"].get("subject") == subject_folder_name

    saved_subject_folder = BIDSFolderModel().load(resp_subject_folder["_id"], user=user, level=AccessType.WRITE)

    assert saved_subject_folder
