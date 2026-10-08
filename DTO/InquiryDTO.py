from sqlmodel import SQLModel, Field
from datetime import datetime,date
class Inquiry(SQLModel, table=True):
    inquiry_id:int| None=Field(
        default=None,
        primary_key=True
    )
    inquiry_title:str=Field(
        max_length=100
    )
    inquiry_detail:str=Field(
        max_length=5000
    )
    inquiry_date:datetime
    inquiry_answer:str | None=Field(
        default=None,
        max_length=2000
    )
    inquiry_answer_date:date | None=None
    
    user_id:str=Field(
        foreign_key='user.user_id'
    )
    inquiry_status_id:int=Field(
        foreign_key='inquiry_status.inquiry_status_id'
    )
    
    inquiry_type:str=Field(
        max_length=5
    )
    