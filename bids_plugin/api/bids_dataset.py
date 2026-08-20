from typing import Any

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, filtermodel
from girder.constants import AccessType, SortDir, TokenScope
from girder.models.collection import Collection
from girder.utility.model_importer import ModelImporter
from pydantic import TypeAdapter
from pymongo.cursor import Cursor

from bids_plugin.models import BIDSDatasetModel
from bids_plugin.utility import BIDSDescription, GirderModel, MongoOperators


class BIDSDatasetResource(Resource):
    """RESTful BIDS dataset resource"""

    def __init__(self) -> None:
        super().__init__()
        self.resourceName = "bids_dataset"
        self._model = BIDSDatasetModel()
        self.route("GET", (), self.list_datasets)
        self.route("POST", (), self.create_dataset)

    @access.user(TokenScope.DATA_READ)
    @filtermodel(model=BIDSDatasetModel)
    @autoDescribeRoute(
        Description("List bids dataset in the database user has access to.")
        .responseClass("BIDSDataset", array=True)
        .modelParam(
            "collection_id",
            "The ID of the root collection.",
            model=Collection,
            level=AccessType.WRITE,
            paramType="query",
            destName="collection",
            required=False,
        )
        .modelParam(
            "parent_id",
            "The ID of the parent.",
            model=BIDSDatasetModel,
            level=AccessType.WRITE,
            paramType="query",
            destName="parent",
            required=False,
        )
        .param(
            "is_derivative",
            "Whether to search for derivative datasets",
            dataType="boolean",
            required=False,
        )
        .param("search_text", "Pass to perform a search.", default="", required=False)
        .param("search_mode", "Search mode", default="prefix", enum=["prefix", "text"], required=False)
        .pagingParams(defaultSort="created", defaultSortDir=SortDir.DESCENDING)
    )
    def list_datasets(
        self,
        collection: GirderModel | None,
        parent: GirderModel | None,
        is_derivative: bool,
        search_text: str,
        search_mode: str,
        limit: int,
        offset: int,
        sort: str,
    ) -> Cursor | Any:
        user = self.getCurrentUser()
        query = {
            "dataset_description": {MongoOperators.exists: True, MongoOperators.notEqual: None},
        }
        if collection is not None:
            query.update({"baseParentId": collection["_id"]})

        if parent is not None:
            query.update({"parentId": parent["_id"]})

        if is_derivative is not None:
            query.update({"dataset_description.DatasetType": "derivative" if is_derivative else "raw"})

        return self._list_datatasets(
            query,
            search_text,
            search_mode,
            offset=offset,
            limit=limit,
            sort=sort,
            user=user,
        )

    def _list_datatasets(self, query: dict[str, Any], search_text: str, search_mode: str, **kwargs) -> Cursor | Any:
        if search_text:
            if search_mode == "prefix":
                return self._model.prefixSearch(query=search_text, filters=query, **kwargs)
            if search_text == "text":
                return self._model.textSearch(query=search_text, filters=query, **kwargs)

        return self._model.find(query=query, **kwargs)

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=BIDSDatasetModel)
    @autoDescribeRoute(
        Description("Create a new BIDS dataset.")
        .responseClass("BIDSDataset")
        .param("parent_id", "The ID of the dataset's parent.")
        .param(
            "parent_type",
            "Type of the dataset's parent",
            required=False,
            enum=["folder", "user", "collection"],
            default="folder",
        )
        .param("name", "Name of the BIDS Dataset.", strip=True)
        .jsonParam(
            "dataset_description",
            "A JSON object containing the dataset description keys to add",
            paramType="form",
            schema=TypeAdapter(BIDSDescription).json_schema(),
        )
        .param(
            "reuse_existing",
            "Return existing BIDS dataset if it exists rather than creating a new one.",
            dataType="boolean",
            required=False,
            default=False,
        )
        .errorResponse()
        .errorResponse("Write access was denied on the parent.", 403)
    )
    def create_dataset(
        self, parent_type: str, parent_id: str, name: str, dataset_description: dict[str, Any], reuse_existing: bool
    ) -> GirderModel:
        user = self.getCurrentUser()
        parent = ModelImporter.model(parent_type).load(id=parent_id, user=user, level=AccessType.WRITE, exc=True)

        dataset_description["Name"] = name
        TypeAdapter(BIDSDescription).validate_python(dataset_description)

        return self._model.create_bids_dataset(
            user,
            name,
            parent,
            BIDSDescription(**dataset_description),
            parent_type=parent_type,
            reuse_existing=reuse_existing,
        )
