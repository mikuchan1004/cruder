from sqlmodel import SQLModel, Field
from typing import Optional
# 댓글 DTO
class JobTipComment(SQLModel, table=True):
    __tablename__ = "job_tip_comment"
    reple_no:int | None=Field(
        default=None,
        primary_key=True
    )
    reple:str=Field(
        max_length=500
    )
   
    parent_reple_no:int | None=Field(
        default=None,
        foreign_key='job_tip_comment.reple_no'
    )
    job_tip_no:int=Field(
        foreign_key='job_tip.job_tip_no'
    )
    user_id:str=Field(
        foreign_key='user.user_id',
        max_length=12
    )