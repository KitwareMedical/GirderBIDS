from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from typing import Any

GirderModel = dict[str, Any]


class BIDSDatatype(Enum):
    UNDEFINED = None
    ANAT = "anat"
    FUNC = "func"
    FMAP = "fmap"
    DWI = "dwi"
    PERF = "perf"
    EEG = "eeg"
    MEG = "meg"
    IEEG = "ieeg"
    BEH = "beh"
    PET = "pet"
    MICR = "micr"
    NIRS = "nirs"
    MOTION = "motion"
    MRS = "mrs"


@dataclass
class BIDSHierarchy:
    is_derivative: bool = False
    subject: str | None = None
    session: str | None = None
    datatype: str | None = None
    suffix: str | None = None
    ext: str | None = None


@dataclass
class Model:
    name: str | None = None

    @classmethod
    def fields(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    def as_dict(self, extra_fields: dict[str, Any] | None = None) -> dict[str, Any]:
        model_dict = asdict(self)

        if isinstance(extra_fields, dict):
            model_dict.update(extra_fields)

        return model_dict


@dataclass
class BIDSDescription:
    Name: str = ""
    BIDSVersion: str = ""
    HEDVersion: str = ""
    DatasetType: str = "raw"
    License: str = ""
    Authors: list = field(default_factory=list)
    Acknowledgements: str = ""
    HowToAcknowledge: str = ""
    Funding: list = field(default_factory=list)
    EthicsApprovals: list = field(default_factory=list)
    ReferencesAndLinks: list = field(default_factory=list)
    DatasetDOI: str = "doi:"


@dataclass
class BIDSItem(Model):
    dataset_id: str | None = None
    source_id: str | None = None
    bids_hierarchy: BIDSHierarchy = field(default_factory=BIDSHierarchy)
    is_metadata: bool = False


@dataclass
class BIDSFolder(Model):
    dataset_id: str | None = None
    bids_hierarchy: BIDSHierarchy = field(default_factory=BIDSHierarchy)


@dataclass
class BIDSDataset(Model):
    dataset_description: BIDSDescription = field(default_factory=BIDSDescription)
    derivatives_folder_id: str | None = None
    bids_hierarchy: BIDSHierarchy = field(default_factory=BIDSHierarchy)
