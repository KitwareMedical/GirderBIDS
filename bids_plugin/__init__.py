from typing import Any

from girder import plugin
from girder.utility.model_importer import ModelImporter

from .api import BIDSDatasetResource, BIDSFolderResource, BIDSItemResource
from .models import BIDSDatasetModel, BIDSFolderModel, BIDSItemModel


class BIDSPlugin(plugin.GirderPlugin):
    def load(self, info: dict[str, Any]) -> None:
        ModelImporter.registerModel("bids_dataset", BIDSDatasetModel, plugin="bids_plugin")
        info["apiRoot"].bids_dataset = BIDSDatasetResource()
        ModelImporter.registerModel("bids_folder", BIDSFolderModel, plugin="bids_plugin")
        info["apiRoot"].bids_folder = BIDSFolderResource()
        ModelImporter.registerModel("bids_item", BIDSItemModel, plugin="bids_plugin")
        info["apiRoot"].bids_item = BIDSItemResource()
