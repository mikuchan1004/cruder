from sqlmodel import SQLModel, Field
# from typing import Optional
from datetime import datetime
class Notice(SQLModel, table=True):
    notice_id:int | None=Field(
        default=None,
        primary_key=True
    )
    notice_title:str=Field(
        max_length=200
    )
    notice_date:str=Field(
        max_length=2000
    )
    notice_date:datetime
    user_id:str=Field(
        foreign_key='user.user_id',
        max_length=12
    )
    
    