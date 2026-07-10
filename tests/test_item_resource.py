from typing import Any

from bson.objectid import ObjectId
from girder.constants import AccessType
from pytest_girder.assertions import assertStatusOk

from bids_plugin.models import BIDSItemModel
from bids_plugin.utility import GirderModel


def test_list_items(db: Any, dataset: GirderModel, item_list: list[GirderModel], server: Any, user: Any) -> None:
    resp = server.request(
        method="GET",
        path="/bids_item",
        params={"dataset_id": dataset["_id"]},
        user=user,
    )

    assertStatusOk(resp)

    resp_item_list = resp.json

    assert len(resp_item_list) == 2
    assert any(it["name"] == item_list[0]["name"] for it in resp_item_list)
    assert any(it["name"] == item_list[1]["name"] for it in resp_item_list)


def test_list_items_matches_suffix(db: Any, dataset: GirderModel, item_list: list[GirderModel], server: Any, user: Any) -> None:
    resp = server.request(
        method="GET",
        path="/bids_item",
        params={"dataset_id": dataset["_id"], "suffix": "analysis1"},
        user=user,
    )

    assertStatusOk(resp)

    resp_item_list = resp.json

    assert len(resp_item_list) == 1
    assert any(it["name"] == item_list[0]["name"] for it in resp_item_list)



def test_create_item(
    db: Any, dataset: GirderModel, datatype_folder: GirderModel, server: Any, user: GirderModel
) -> None:
    item_name = "sub-01_task-rest_analysis.nii.gz"
    resp = server.request(
        method="POST",
        path="/bids_item",
        params={
            "dataset_id": dataset["_id"],
            "folder_id": datatype_folder["_id"],
            "name": item_name,
        },
        user=user,
    )
    resp_item = resp.json

    assertStatusOk(resp)
    assert resp_item["name"] == item_name
    assert ObjectId(resp_item["creatorId"]) == user["_id"]
    assert ObjectId(resp_item["folderId"]) == datatype_folder["_id"]
    assert ObjectId(resp_item.get("dataset_id")) == dataset["_id"]
    assert resp_item.get("bids_hierarchy")
    assert "is_metadata" in resp_item
    assert "source_id" in resp_item

    saved_item = BIDSItemModel().load(resp_item["_id"], user=user, level=AccessType.WRITE)

    assert saved_item
