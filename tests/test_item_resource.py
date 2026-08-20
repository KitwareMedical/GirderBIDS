import json
from typing import Any

from bson.objectid import ObjectId
from girder import events
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


def test_list_items_matches_suffix(
    db: Any, dataset: GirderModel, item_list: list[GirderModel], server: Any, user: Any
) -> None:
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
    assert resp_item_list[0]["suffix"] == "analysis1"


def test_search_list_items(db: Any, dataset: GirderModel, item_list: list[GirderModel], server: Any, user: Any) -> None:
    resp = server.request(
        method="GET",
        path="/bids_item",
        params={"dataset_id": dataset["_id"], "search_text": "sub-01_task-rest_analysis1"},
        user=user,
    )

    assertStatusOk(resp)

    resp_item_list = resp.json

    assert len(resp_item_list) == 1
    assert any(it["name"] == item_list[0]["name"] for it in resp_item_list)
    assert resp_item_list[0]["suffix"] == "analysis1"


def test_create_item(
    db: Any, dataset: GirderModel, datatype_folder: GirderModel, server: Any, user: GirderModel
) -> None:
    item_name = "sub-01_task-rest_analysis.nii.gz"
    resp = server.request(
        method="POST",
        path="/bids_item",
        params={
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
    assert "source_id" in resp_item
    assert resp_item["suffix"] == "analysis"
    assert resp_item["extension"] == "nii.gz"

    saved_item = BIDSItemModel().load(resp_item["_id"], user=user, level=AccessType.WRITE)

    assert saved_item


def test_update_item_bids_metadata(db: Any, item_list: list[GirderModel], server: Any, user: GirderModel) -> None:
    events.unbindAll()  # Need to unbind JSON file creation for tests (no assetstore)
    item = item_list[0]
    resp = server.request(
        method="PUT",
        path=f"/bids_item/{item['_id']}/metadata",
        params={"metadata": json.dumps({"new_key": "new_value"})},
        user=user,
    )
    resp_item = resp.json

    assertStatusOk(resp)
    assert ObjectId(resp_item["_id"]) == item["_id"]
    assert "new_key" in resp_item["bids_metadata"]
    assert "new_key" not in resp_item["meta"]
    assert resp_item["bids_metadata"]["new_key"] == "new_value"
