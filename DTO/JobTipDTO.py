from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
# 취업 꿀팀 게시판 Dto
# auto_increment 들어가는 곳은 기본값 none이라고 설정하기
class JobTip(SQLModel,table=True):
    job_tip_no:int| None=Field(
        default=None,
        primary_key=True
    )
    job_tip_title:str=Field(
        max_length=200
    )
    job_tip_date:datetime
    job_tip_detail:str
    job_tip_attachment:str | None=None
    user_id:str=Field(
        foreign_key='user.user_id',
        max_length=12
    )