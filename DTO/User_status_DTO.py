from sqlmodel import SQLModel, Field
from typing import Optional
# 유저상태 테이블 DTO
class UserStatus(SQLModel,table=True):
    user_status_id:int=Field(
		primary_key = True,  
	)
    user_status_name:str=Field(
        max_length=5
    )
    
    user_status_code:int
    