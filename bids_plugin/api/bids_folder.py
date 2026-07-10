from typing import Any

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, filtermodel
from girder.constants import AccessType, SortDir, TokenScope
from girder.exceptions import GirderException
from girder.models.folder import Folder
from pydantic import TypeAdapter
from pymongo.cursor import Cursor

from bids_plugin.models import BIDSDatasetModel, BIDSFolderModel
from bids_plugin.utility import GirderModel
from bids_plugin.utility.models import BIDSHierarchy


class BIDSFolderResource(Resource):
    """RESTful Case resource"""

    def __init__(self) -> None:
        super().__init__()
        self.resourceName = "bids_folder"
        self._model = BIDSFolderModel()
        self.route("GET", (), self.list_folders)
        self.route("POST", (), self.create_folder)
        self.route("POST", ("hierarchy",), self.create_folder_from_hierarchy)

    @access.user(TokenScope.DATA_READ)
    @filtermodel(model=BIDSFolderModel)
    @autoDescribeRoute(
        Description("List bids folder in a BIDS dataset user has access to.")
        .responseClass("BIDSFolder", array=True)
        .modelParam(
            "dataset_id",
            "The ID of the root BIDS dataset",
            model=BIDSDatasetModel,
            level=AccessType.WRITE,
            paramType="query",
            destName="dataset",
        )
        .jsonParam(
            "bids_hierarchy",
            "An optional JSON object containing the hierarchy to search",
            paramType="form",
            schema=TypeAdapter(BIDSHierarchy).json_schema(),
            required=False,
        )
        .pagingParams(defaultSort="created", defaultSortDir=SortDir.DESCENDING)
    )
    def list_folders(self, dataset: GirderModel, bids_hierarchy: dict[str, Any] | None, limit: int, offset: int, sort: str) -> Cursor | Any:
        user = self.getCurrentUser()
        query = {"dataset_id": dataset["_id"]}
        
        if bids_hierarchy is not None:
            TypeAdapter(BIDSHierarchy).validate_python(bids_hierarchy)
            query.update({f"bids_hierarchy.{key}": value for key, value in bids_hierarchy.items()})

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
            "dataset_id",
            "The ID of the root BIDS dataset",
            model=BIDSDatasetModel,
            level=AccessType.WRITE,
            paramType="query",
            destName="dataset",
        )
        .modelParam(
            "folder_id",
            "The ID of the parent folder.",
            model=Folder,
            level=AccessType.WRITE,
            paramType="query",
            destName="folder",
        )
        .param("name", "Name of the BIDS Folder.", strip=True)
        .errorResponse()
        .errorResponse("Write access was denied on the parent.", 403)
    )
    def create_folder(
        self,
        dataset: GirderModel,
        folder: GirderModel,
        name: str,
    ) -> GirderModel:
        user = self.getCurrentUser()
        return self._model.create_bids_folder(
            user,
            name,
            dataset,
            folder,
        )

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=BIDSFolderModel)
    @autoDescribeRoute(
        Description("Create a new BIDS dataset.")
        .responseClass("BIDSFolder")
        .modelParam(
            "dataset_id",
            "The ID of the root BIDS dataset",
            model=BIDSDatasetModel,
            level=AccessType.WRITE,
            paramType="query",
            destName="dataset",
        )
        .jsonParam(
            "bids_hierarchy",
            "An optional JSON object containing the hierarchy to search",
            paramType="form",
            schema=TypeAdapter(BIDSHierarchy).json_schema(),
        )
        .param("name", "Name of the BIDS Folder.", strip=True)
        .errorResponse()
        .errorResponse("Write access was denied on the parent.", 403)
    )
    def create_folder_from_hierarchy(
        self,
        dataset: GirderModel,
        bids_hierarchy: dict[str, Any],
    ) -> GirderModel:
        user = self.getCurrentUser()
        TypeAdapter(BIDSHierarchy).validate_python(bids_hierarchy)

        if bids_hierarchy["subject"] is None:
            raise GirderException("Invalid BIDS hierarchy: must at least specify a subject")

        parent = dataset
        last_folder = dataset

        for level in ("subject", "session", "datatype"):
            name = bids_hierarchy[level]
            if name is None:
                continue
            
            last_folder = next(self._model.find(query={"name": name, "parentId": parent}), None)
            if last_folder is None:
                last_folder = self._model.create_bids_folder(
                    user,
                    name,
                    dataset,
                    parent,
                )
            parent = last_folder

        return last_folder
    

        
