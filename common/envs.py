from os import getenv

ABAN_BACKEND_REDIS_HOST = getenv('ABAN_BACKEND_REDIS_HOST', '127.0.0.1')
ABAN_BACKEND_REDIS_PORT = getenv('ABAN_BACKEND_REDIS_PORT', '6379')