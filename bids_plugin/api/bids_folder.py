from typing import Any

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, filtermodel
from girder.constants import AccessType, SortDir, TokenScope
from girder.models.folder import Folder
from pymongo.cursor import Cursor

from bids_plugin.models import BIDSDatasetModel, BIDSFolderModel
from bids_plugin.utility import GirderModel


class BIDSFolderResource(Resource):
    """RESTful BIDS Folder resource"""

    def __init__(self) -> None:
        super().__init__()
        self.resourceName = "bids_folder"
        self._model = BIDSFolderModel()
        self.route("GET", (), self.list_folders)
        self.route("POST", (), self.create_folder)

    @access.user(TokenScope.DATA_READ)
    @filtermodel(model=BIDSFolderModel)
    @autoDescribeRoute(
        Description("List bids folder in a BIDS dataset user has access to.")
        .responseClass("BIDSFolder", array=True)
        .modelParam(
            "dataset_id",
            "The ID of the root BIDS dataset",
            model=BIDSDatasetModel,
            level=AccessType.READ,
            paramType="query",
            destName="dataset",
        )
        .pagingParams(defaultSort="created", defaultSortDir=SortDir.DESCENDING)
    )
    def list_folders(self, dataset: GirderModel, limit: int, offset: int, sort: str) -> Cursor | Any:
        user = self.getCurrentUser()
        query = {"dataset_id": dataset["_id"]}

        return self._model.find(
            query=query,
            limit=limit,
            offset=offset,
            sort=sort,
            user=user,
        )

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=BIDSFolderModel)
    @autoDescribeRoute(
        Description("Create a new BIDS dataset.")
        .responseClass("BIDSFolder")
        .modelParam(
            "folder_id",
            "The ID of the parent folder.",
            model=Folder,
            level=AccessType.WRITE,
            paramType="query",
            destName="folder",
        )
        .param("name", "Name of the BIDS Folder.", strip=True)
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
    def create_folder(
        self,
        folder: GirderModel,
        name: str,
        reuse_existing: bool,
    ) -> GirderModel:
        user = self.getCurrentUser()
        return self._model.create_bids_folder(
            user,
            name,
            folder,
            reuse_existing=reuse_existing,
        )
