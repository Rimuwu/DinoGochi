from typing import Mapping, Any, Optional, Sequence
from motor.core import AgnosticClientSession
from pymongo.typings import _CollationIn, _Pipeline
from motor.motor_asyncio import AsyncIOMotorCollection
from bson.raw_bson import RawBSONDocument

from bot.modules.logs import log
from time import time as time_now


class DBconstructor(AsyncIOMotorCollection):

    def __init__(self, db_collection: AsyncIOMotorCollection):
        self.db_collection = db_collection

    async def update_one(self, 
        filter: Mapping[str, Any],
        update: Mapping[str, Any] | _Pipeline,
        upsert: bool = False,
        bypass_document_validation: bool = False,
        collation: _CollationIn | None = None,
        array_filters: Sequence[Mapping[str, Any]] | None = None,
        hint: Any | None = None,
        session: AgnosticClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = None):

        tt = time_now()
        dat = await self.db_collection.update_one(filter, update, upsert, bypass_document_validation, collation, array_filters, hint, session, let)
        tt = time_now() - tt

        log(lvl=-1, prefix="update_one", 
            message=f'[{comment}]   {self.db_collection.name}   {update}   {filter}   {round(tt, 2)}   modif: {dat.modified_count}')

        return dat

    async def update_many(self,
        filter: Mapping[str, Any],
        update: Mapping[str, Any] | _Pipeline,
        upsert: bool = False,
        array_filters: Sequence[Mapping[str, Any]] | None = None,
        bypass_document_validation: bool | None = None,
        collation: _CollationIn | None = None,
        hint: Any | None = None,
        session: AgnosticClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = 'NoComment'):

        tt = time_now()
        dat = await self.db_collection.update_many(filter, update, upsert, array_filters, bypass_document_validation, collation, hint, session, let)
        tt = time_now() - tt

        log(lvl=-1, prefix="update_many", 
            message=f'[{comment}]   {self.db_collection.name}   {update}   {filter}   {round(tt, 2)}   modif: {dat.modified_count}')

        return dat

    async def insert_one(self,
        document: Any | RawBSONDocument,
        bypass_document_validation: bool = False,
        session: AgnosticClientSession | None = None,
        comment: Any | None = 'NoComment'):

        tt = time_now()
        dat = await self.db_collection.insert_one(document, bypass_document_validation,
                                                  session)
        tt = time_now() - tt

        log(lvl=-1, prefix="insert_one", 
            message=f'[{comment}]   {self.db_collection.name}   {document}   {round(tt, 2)}   inserted_id: {dat.inserted_id}')

        return dat

    async def find_one(self,
        filter: Optional[Any] = None, *args,
        comment: Any | None = 'NoComment'):

        tt = time_now()
        dat = await self.db_collection.find_one(filter, *args)
        tt = time_now() - tt

        log(lvl=-1, prefix="find_one", 
            message=f'[{comment}]   {self.db_collection.name}   {filter}   {round(tt, 5)}   {str(dat)[:80]}')

        return dat

    async def find(self,
        filter: Optional[Any] = None, *args,
        comment: Any | None = 'NoComment',
        skip: int = 0, max_col: Optional[int] = 0
        ):

        tt = time_now()
        dat = await self.db_collection.find(filter, *args).skip(skip).to_list(max_col)
        tt = time_now() - tt

        log(lvl=-1, prefix="find", 
            message=f'[{comment}]   {self.db_collection.name}   {filter}   {round(tt, 2)}')

        return dat

    async def delete_one(self, 
        filter: Mapping[str, Any],
        collation: _CollationIn | None = None,
        hint: Any | None = None,
        session: AgnosticClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = 'NoComment'):

        tt = time_now()
        dat = await self.db_collection.delete_one(filter, collation, 
                                                  hint, session, let)
        tt = time_now() - tt

        log(lvl=-1, prefix="delete_one", 
            message=f'[{comment}]   {self.db_collection.name}   {filter}   {round(tt, 2)}')

        return dat

    async def delete_many(self, 
        filter: Mapping[str, Any],
        collation: _CollationIn | None = None,
        hint: Any | None = None,
        session: AgnosticClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = 'NoComment'):

        tt = time_now()
        dat = await self.db_collection.delete_many(filter, collation, 
                                                   hint, session, let)
        tt = time_now() - tt

        log(lvl=-1, prefix="delete_many", 
            message=f'[{comment}]   {self.db_collection.name}   {filter}   {round(tt, 2)}')

        return dat

    async def count_documents(self,
        filter: Mapping[str, Any],
        session: AgnosticClientSession | None = None,
        comment: Any | None = "NoComment",
        **kwargs: Any):

        tt = time_now()
        dat = await self.db_collection.count_documents(filter, session, **kwargs)
        tt = time_now() - tt

        log(lvl=-1, prefix="count_documents", 
            message=f'[{comment}]   {self.db_collection.name}   {filter}   {round(tt, 2)}   count: {dat}')

        return dat
