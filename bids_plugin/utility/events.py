import io
import json
from datetime import datetime, timezone

from girder.events import Event
from girder.exceptions import ValidationException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.upload import Upload
from girder.models.user import User

from .models import JSON_EXT

file_model = File()
user_model = User()
folder_model = Folder()
item_model = Item()
upload_model = Upload()


def on_bids_metadata_updated(event: Event) -> None:
    item = event.info
    if item["extension"] == JSON_EXT:
        raise ValidationException("JSON items cannot have a JSON sidecar")

    metadata_sidecar_name = item["name"].removesuffix(item["extension"]) + JSON_EXT

    folder = folder_model.load(item["folderId"], force=True)
    user = user_model.load(item["creatorId"], force=True)

    metadata_sidecar_item = item_model.createItem(metadata_sidecar_name, user, folder, reuseExisting=True)

    json_bytes = json.dumps(item["bids_metadata"], indent=4).encode("utf-8")
    stream = io.BytesIO(json_bytes)
    size = len(json_bytes)

    existing_file = None
    for file_obj in item_model.childFiles(metadata_sidecar_item):
        if file_obj["name"] == metadata_sidecar_name:
            existing_file = file_obj
            break

    if existing_file:
        file_model.remove(existing_file)

    upload_model.uploadFromFile(
        obj=stream,
        size=size,
        name=metadata_sidecar_name,
        parentType="item",
        parent=metadata_sidecar_item,
        user=user,
    )

    metadata_sidecar_item["updated"] = datetime.now(timezone.utc)
    item_model.save(metadata_sidecar_item)
