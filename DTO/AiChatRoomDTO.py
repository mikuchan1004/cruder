from sqlmodel import SQLModel, Field
from datetime import date

class AiChatRoom(SQLModel, table=True):
  __tablename__ = "ai_chat_room"
  ai_chat_id:int|None=Field(
      default=None,
      primary_key=True
  )
  ai_chat_date:date|None=None
  user_id:str=Field(
      foreign_key='user.user_id'
  )