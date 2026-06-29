class LazyCollection:
    def __init__(self, model_cls):
        self._model_cls = model_cls

    def __getattr__(self, name):
        settings = self._model_cls.get_settings()
        collection = settings.motor_db[settings.name]
        return getattr(collection, name)

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
