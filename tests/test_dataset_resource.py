from typing import Any

from bson.objectid import ObjectId
from girder.constants import AccessType
from pydantic import TypeAdapter
from pytest_girder.assertions import assertStatusOk

from bids_plugin.models import BIDSDatasetModel
from bids_plugin.utility import BIDSDescription, GirderModel


def test_list_all_datasets(
    db: Any, collection: GirderModel, dataset_list: list[GirderModel], server: Any, user: Any
) -> None:
    resp = server.request(
        method="GET",
        path="/bids_dataset",
        params={"collection_id": collection["_id"]},
        user=user,
    )

    assertStatusOk(resp)

    resp_dataset_list = resp.json

    assert len(resp_dataset_list) == 3
    assert any(ds["name"] == dataset_list[0]["name"] for ds in resp_dataset_list)
    assert any(ds["name"] == dataset_list[1]["name"] for ds in resp_dataset_list)
    assert any(ds["name"] == dataset_list[2]["name"] for ds in resp_dataset_list)


def test_list_raw_datasets(
    db: Any, collection: GirderModel, dataset_list: list[GirderModel], server: Any, user: GirderModel
) -> None:
    resp = server.request(
        method="GET",
        path="/bids_dataset",
        params={"collection_id": collection["_id"], "is_derivative": False},
        user=user,
    )

    assertStatusOk(resp)

    resp_dataset_list = resp.json

    assert len(resp_dataset_list) == 2
    assert any(ds["name"] == dataset_list[0]["name"] for ds in resp_dataset_list)
    assert any(ds["name"] == dataset_list[1]["name"] for ds in resp_dataset_list)
    assert not any(ds["name"] == dataset_list[2]["name"] for ds in resp_dataset_list)


def test_list_derivative_datasets(
    db: Any, collection: GirderModel, dataset_list: list[GirderModel], server: Any, user: GirderModel
) -> None:
    resp = server.request(
        method="GET",
        path="/bids_dataset",
        params={"collection_id": collection["_id"], "is_derivative": True},
        user=user,
    )

    assertStatusOk(resp)

    resp_dataset_list = resp.json

    assert len(resp_dataset_list) == 1
    assert not any(ds["name"] == dataset_list[0]["name"] for ds in resp_dataset_list)
    assert not any(ds["name"] == dataset_list[1]["name"] for ds in resp_dataset_list)
    assert any(ds["name"] == dataset_list[2]["name"] for ds in resp_dataset_list)



def test_create_dataset(
    db: Any, collection: GirderModel, raw_dataset_description: BIDSDescription, server: Any, user: GirderModel
) -> None:
    dataset_name = "Test Dataset"
    raw_dataset_description.Name = dataset_name
    resp = server.request(
        method="POST",
        path="/bids_dataset",
        params={
            "name": dataset_name,
            "parent_id": collection["_id"],
            "parent_type": "collection",
            "dataset_description": TypeAdapter(BIDSDescription).dump_json(raw_dataset_description),
        },
        user=user,
    )
    resp_dataset = resp.json

    assertStatusOk(resp)
    assert resp_dataset["name"] == dataset_name
    assert ObjectId(resp_dataset["creatorId"]) == user["_id"]
    assert "dataset_description" in resp_dataset

    saved_dataset = BIDSDatasetModel().load(resp_dataset["_id"], user=user, level=AccessType.WRITE)

    assert saved_dataset
