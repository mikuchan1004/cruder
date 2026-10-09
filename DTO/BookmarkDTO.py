from sqlmodel import SQLModel, Field

class BookMark(SQLModel,table=True):
    user_id:str |None=Field(
        primary_key = True,
        foreign_key='user.user_id',
        max_length=12
    )
    recrut_pblnt_sn: str=Field(

            primary_key = True,
            foreign_key='jobs.recrut_pblnt_sn',
            max_length=20
         
    )