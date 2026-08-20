from typing import Any

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, filtermodel
from girder.constants import AccessType, SortDir, TokenScope
from pymongo.cursor import Cursor

from bids_plugin.models import BIDSDatasetModel, BIDSFolderModel, BIDSItemModel
from bids_plugin.utility import GirderModel


class BIDSItemResource(Resource):
    """RESTful BIDS Item resource"""

    def __init__(self) -> None:
        super().__init__()
        self.resourceName = "bids_item"
        self._model = BIDSItemModel()
        self.route("GET", (), self.list_items)
        self.route("GET", (":id", "path"), self.get_dataset_path)
        self.route("PUT", (":id", "metadata"), self.set_bids_metadata)
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
            "The ID of the source BIDS item",
            model=BIDSItemModel,
            level=AccessType.READ,
            paramType="query",
            destName="source",
            required=False,
        )
        .param(
            "name",
            "The name of the BIDS item to search for",
            dataType="boolean",
            required=False,
            strip=True,
        )
        .param("suffix", "Pass this to search BIDS item by suffix", required=False)
        .param("extension", "Pass this to search BIDS item by extension", required=False)
        .param("search_text", "Pass to perform a search.", default="", required=False)
        .param("search_mode", "Search mode", default="prefix", required=False)
        .pagingParams(defaultSort="name", defaultSortDir=SortDir.ASCENDING)
    )
    def list_items(
        self,
        dataset: GirderModel,
        source: GirderModel | None,
        name: str | None,
        suffix: str | None,
        extension: str | None,
        search_text: str,
        search_mode: str,
        limit: int,
        offset: int,
        sort: Any,
    ) -> Cursor | Any:
        user = self.getCurrentUser()
        query = {"dataset_id": dataset["_id"]}
        if source is not None:
            query.update({"source_id": source["_id"]})

        if name is not None:
            query.update({"name": name})

        if suffix is not None:
            query.update({"suffix": suffix})

        if extension is not None:
            query.update({"extension": extension})

        return self._list_items(
            query,
            search_text,
            search_mode,
            limit=limit,
            offset=offset,
            sort=sort,
            user=user,
        )

    def _list_items(self, query: dict[str, Any], search_text: str, search_mode: str, **kwargs) -> Cursor | Any:
        if search_text:
            if search_mode == "prefix":
                return self._model.prefixSearch(query=search_text, filters=query, **kwargs)
            if search_text == "text":
                return self._model.textSearch(query=search_text, filters=query, **kwargs)

        return self._model.find(query=query, **kwargs)

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=BIDSItemModel)
    @autoDescribeRoute(
        Description("Create a new BIDS item.")
        .responseClass("BIDSItem")
        .param("name", "Name of the BIDS item.", strip=True)
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
            "reuse_existing",
            "Return existing BIDS folder if it exists rather than creating a new one.",
            dataType="boolean",
            required=False,
            default=False,
        )
        .errorResponse()
        .errorResponse("Write access was denied on the parent.", 403)
    )
    def create_item(
        self,
        name: str,
        folder: GirderModel,
        source: GirderModel | None,
        reuse_existing: bool,
    ) -> GirderModel:
        user = self.getCurrentUser()

        return self._model.create_bids_item(
            user,
            name,
            folder,
            source,
            reuse_existing,
        )

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description("Get the path to BIDS dataset of the item.")
        .modelParam("id", model=BIDSItemModel, level=AccessType.READ, destName="item")
        .errorResponse("ID was invalid.")
        .errorResponse("Read access was denied for the item.", 403)
    )
    def get_dataset_path(self, item: GirderModel) -> list[GirderModel]:
        return self._model.parents_to_dataset(item, self.getCurrentUser())

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=BIDSItemModel)
    @autoDescribeRoute(
        Description("Set bids_metadata fields on a BIDS item.")
        .responseClass("BIDSItem")
        .modelParam("id", model=BIDSItemModel, level=AccessType.WRITE)
        .jsonParam(
            "metadata", "A JSON object containing the bids metadata keys to add", paramType="body", requireObject=True
        )
        .errorResponse(("ID was invalid.", "Invalid JSON passed in request body.", "Metadata key name was invalid."))
        .errorResponse("Write access was denied for the item.", 403)
    )
    def set_bids_metadata(self, item: GirderModel, metadata: dict[str, Any]) -> GirderModel | Any:
        return self._model.set_bids_metadata(item, metadata)
