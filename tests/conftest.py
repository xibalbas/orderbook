import pytest
import redis

from orderbook.orderbook import OrderBook

@pytest.fixture(scope='module')
def redis_fixture():
    return redis.StrictRedis(host='localhost', 
                             port=6379, db=2, 
                             encoding='utf-8', 
                             decode_responses=True
                             )

@pytest.fixture(scope='function')
def ob(redis_fixture, request):
    def fin():
        redis_fixture.flushdb()
    request.addfinalizer(fin)
    
    return OrderBook('BTC', 'USDT', redis_fixture)

@pytest.fixture(scope='function')
def testOrderbook(redis_fixture):
    return OrderBook('BTC', 'USDT', redis_fixture)
