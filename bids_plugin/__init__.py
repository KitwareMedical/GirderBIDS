from typing import Any

from girder import events, plugin
from girder.utility.model_importer import ModelImporter

from .api import BIDSDatasetResource, BIDSFolderResource, BIDSItemResource
from .models import BIDSDatasetModel, BIDSFolderModel, BIDSItemModel
from .utility import on_bids_metadata_updated, on_item_removed


class BIDSPlugin(plugin.GirderPlugin):
    def load(self, info: dict[str, Any]) -> None:
        ModelImporter.registerModel("bids_dataset", BIDSDatasetModel, plugin="bids_plugin")
        info["apiRoot"].bids_dataset = BIDSDatasetResource()
        ModelImporter.registerModel("bids_folder", BIDSFolderModel, plugin="bids_plugin")
        info["apiRoot"].bids_folder = BIDSFolderResource()
        ModelImporter.registerModel("bids_item", BIDSItemModel, plugin="bids_plugin")
        info["apiRoot"].bids_item = BIDSItemResource()

        events.bind("model.bids_item.bids_metadata.updated", "onBIDSMetadataUpdated", on_bids_metadata_updated)
        events.bind("model.item.remove", "onItemRemoved", on_item_removed)
