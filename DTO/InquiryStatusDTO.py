from sqlmodel import SQLModel, Field

class InquiryStatus(SQLModel, table=True):
    __tablename__ = "inquiry_status"
    inquiry_status_id:int|None=Field(
        default=None,
        primary_key=True
    )
    inquiry_status_name:str=Field(
        max_length=5
    )