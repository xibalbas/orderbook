from redis import StrictRedis
from common.envs import *

class RedisManager:
    def __init__(self, db, *args, **kwargs):

        self._connection = StrictRedis(
            host=ABAN_BACKEND_REDIS_HOST, port=ABAN_BACKEND_REDIS_PORT,
            db=db, decode_responses=True, charset="utf-8"
            )
        return self._connection

    def set(self, key, value):
        self._connection.set(key, value)

    def get(self, key):
        return self._connection.get(key)

    def delete(self, key):
        self._connection.delete(key)