from typing import Any

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, filtermodel
from girder.constants import AccessType, SortDir, TokenScope
from pydantic import TypeAdapter
from pymongo.cursor import Cursor

from bids_plugin.models import BIDSDatasetModel, BIDSFolderModel, BIDSItemModel
from bids_plugin.utility import BIDSHierarchy, GirderModel


class BIDSItemResource(Resource):
    """RESTful Case resource"""

    def __init__(self) -> None:
        super().__init__()
        self.resourceName = "bids_item"
        self._model = BIDSItemModel()
        self.route("GET", (), self.list_items)
        self.route("POST", (), self.create_item)

    @access.user(TokenScope.DATA_READ)
    @filtermodel(model=BIDSItemModel)
    @autoDescribeRoute(
        Description("List bids item in the database user has access to.")
        .responseClass("BIDSItem", array=True)
        .modelParam(
            "dataset_id",
            "The ID of the root BIDS dataset",
            model=BIDSDatasetModel,
            level=AccessType.WRITE,
            paramType="query",
            destName="dataset",
        )
        .modelParam(
            "source_id",
            "The ID of the source item",
            model=BIDSItemModel,
            level=AccessType.READ,
            paramType="query",
            destName="source",
            required=False,
        )
        .jsonParam(
            "bids_hierarchy",
            "An optional JSON object containing the hierarchy to search",
            paramType="form",
            schema=TypeAdapter(BIDSHierarchy).json_schema(),
            required=False,
        )
        .param(
            "is_metadata",
            "Whether to list metadata items",
            dataType="boolean",
            required=False,
            strip=True,
        )
        .param(
            "suffix",
            "Pass this to search BIDS item by suffix",
            required=False
        )
        .param(
            "extension",
            "Pass this to search BIDS item by extension",
            required=False
        )
        .pagingParams(defaultSort="created", defaultSortDir=SortDir.DESCENDING)
    )
    def list_items(
        self,
        dataset: GirderModel,
        source: GirderModel | None,
        bids_hierarchy: dict[str, Any] | None,
        is_metadata: bool | None,
        suffix: str | None,
        extension: str | None,
        limit: int,
        offset: int,
        sort: Any,
    ) -> Cursor | Any:
        user = self.getCurrentUser()
        query = {"dataset_id": dataset["_id"]}
        if source is not None:
            query.update({"source_id": source["_id"]})

        if bids_hierarchy is not None:
            TypeAdapter(BIDSHierarchy).validate_python(bids_hierarchy)
            query.update({f"bids_hierarchy.{key}": value for key, value in bids_hierarchy.items()})

        if is_metadata is not None:
            query.update({"is_metadata": is_metadata})

        if suffix is not None:
            query.update({"bids_hierarchy.suffix": suffix})

        if extension is not None:
            query.update({"bids_hierarchy.ext": extension})

        return self._model.find(
            query=query,
            limit=limit,
            offset=offset,
            sort=sort,
            user=user,
        )

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=BIDSItemModel)
    @autoDescribeRoute(
        Description("Create a new BIDS item.")
        .responseClass("BIDSItem")
        .param("name", "Name of the BIDS item.", strip=True)
        .modelParam(
            "dataset_id",
            "The ID of the root BIDS dataset",
            model=BIDSDatasetModel,
            level=AccessType.WRITE,
            paramType="query",
            destName="dataset",
        )
        .modelParam(
            "folder_id",
            "The ID of the parent BIDS folder.",
            model=BIDSFolderModel,
            level=AccessType.WRITE,
            paramType="query",
            destName="folder",
        )
        .modelParam(
            "source_id",
            "The ID of the optional source item.",
            model=BIDSItemModel,
            level=AccessType.WRITE,
            paramType="query",
            destName="source",
            required=False,
        )
        .param(
            "is_metadata",
            "Whether the item defines a metadata file",
            dataType="boolean",
            required=False,
            default=False,
            strip=True,
        )
        .errorResponse()
        .errorResponse("Write access was denied on the parent.", 403)
    )
    def create_item(
        self,
        name: str,
        dataset: GirderModel,
        folder: GirderModel,
        source: GirderModel | None,
        is_metadata: bool,
    ) -> GirderModel:
        user = self.getCurrentUser()

        return self._model.create_bids_item(
            user,
            name,
            dataset,
            folder,
            source,
            is_metadata=is_metadata,
        )
