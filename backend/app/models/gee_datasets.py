from pydantic import BaseModel


class DatasetBandStatus(BaseModel):
    dataset_id: str
    accessible: bool
    image_count: int | None = None
    required_bands_available: bool | None = None
    message: str | None = None


class DatasetAccessStatus(BaseModel):
    dataset_id: str
    accessible: bool
    message: str | None = None


class DatasetMaskStatus(BaseModel):
    dataset_id: str
    source: str
    accessible: bool
    asset_type: str | None = None
    band_names: list[str] | None = None
    usable_as_mask: bool | None = None
    message: str | None = None


class GeeDatasetsStatusResponse(BaseModel):
    connected: bool
    status: str
    study_area: dict
    date_range: dict
    datasets: dict
    processing_performed: bool
    message: str
