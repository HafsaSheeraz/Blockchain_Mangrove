from pydantic import BaseModel


class GeeStatusResponse(BaseModel):
    enabled: bool
    connected: bool
    status: str
    project_id: str | None = None
    message: str | None = None
