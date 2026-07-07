class LazyCollection:
    def __init__(self, model_cls):
        self._model_cls = model_cls

    def __getattr__(self, name):
        settings = self._model_cls.get_settings()
        collection = settings.pymongo_collection
        return getattr(collection, name)

    def __getitem__(self, item):
        settings = self._model_cls.get_settings()
        return settings.pymongo_collection[item]

    async def find(self, filter=None, *args, comment='NoComment', max_col=None, **kwargs):
        settings = self._model_cls.get_settings()
        collection = settings.pymongo_collection
        cursor = collection.find(filter, *args, comment=comment, **kwargs)
        res = await cursor.to_list(max_col)
        for doc in res:
            if 'dino' in doc and doc['dino'] is not None:
                dino_val = doc['dino']
                if hasattr(dino_val, 'id'):
                    doc['dino_id'] = dino_val.id
                elif isinstance(dino_val, dict) and '$id' in dino_val:
                    doc['dino_id'] = dino_val['$id']
        return res

    async def find_one(self, filter=None, *args, **kwargs):
        settings = self._model_cls.get_settings()
        collection = settings.pymongo_collection
        doc = await collection.find_one(filter, *args, **kwargs)
        if doc and 'dino' in doc and doc['dino'] is not None:
            dino_val = doc['dino']
            if hasattr(dino_val, 'id'):
                doc['dino_id'] = dino_val.id
            elif isinstance(dino_val, dict) and '$id' in dino_val:
                doc['dino_id'] = dino_val['$id']
        return doc

class RawLazyCollection:
    def __init__(self, collection_name: str):
        self._collection_name = collection_name

    @property
    def _collection(self):
        from bot.dbmanager import mongo_client
        return mongo_client.dinogochi[self._collection_name]

    def __getattr__(self, name):
        return getattr(self._collection, name)

    def __getitem__(self, item):
        return self._collection[item]

    async def find(self, filter=None, *args, comment='NoComment', max_col=None, **kwargs):
        cursor = self._collection.find(filter, *args, comment=comment, **kwargs)
        return await cursor.to_list(max_col)

class Transaction:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        from bot.dbmanager import mongo_client
        try:
            self.session = await mongo_client.start_session()
            self.session.start_transaction()
        except Exception:
            self.session = None
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type is not None:
                try:
                    await self.session.abort_transaction()
                except Exception: pass
            else:
                try:
                    await self.session.commit_transaction()
                except Exception: pass
            await self.session.end_session()
