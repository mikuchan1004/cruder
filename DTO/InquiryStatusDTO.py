from sqlmodel import SQLModel, Field

class Inquiry(SQLModel, table=True):
    inquiry_status_id:int|None=Field(
        default=None,
        primary_key=True
    )
    inquiry_status_name:str=Field(
        max_length=5
    )