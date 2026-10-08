from sqlmodel import SQLModel, Field
from typing import Optional
# userDTO 설계
class User(SQLModel,table=True):
     
    user_id:str | None=Field(
		primary_key = True,
        max_length=12
  
	)
    user_name:str=Field(
        max_length=20
    )
    user_pw:str=Field(
        max_length=255
    )
    user_phone:str=Field(
        max_length=30
    )
    user_status_id:int=Field(
          foreign_key='user_status.user_status_id',
    )
    user_home:str=Field(
        max_length=50
    )
    user_email:str=Field(
        max_length=40
    )