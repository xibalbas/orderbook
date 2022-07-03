"""
TO TEST:
    bid/asks executed at equal price?
    market orders
"""
import pytest

from orderbook.orderbook import Bid, Ask, OrderQuantityError, OrderPriceError

def test_ping(red):
    assert red.ping()

def test_empty_orderbook(ob):
    assert ob.get_best_ask() == 0
    assert ob.get_worst_ask() == 0
    assert ob.get_best_bid() == 0
    assert ob.get_worst_bid() == 0
    #assert ob.getBidVolume() == 0
    #assert ob.getAskVolume() == 0
    #FIXME value, others?

def test_empty_orderbook_level1_data(ob):
    assert 1

def test_empty_orderbook_level2_data(ob):
    assert 1

def test_ask_order(ob):
    o = Ask(1, 960, 'Alice')
    ts, oib = ob.process_order(o)
    assert len(ts) == 0
    assert oib.qty == o.qty 
    assert oib.price == o.price
    assert oib.trader_id == o.trader_id
    assert oib.timestamp is not None
    assert oib.order_id is not None
    assert ob.get_best_ask() == o.price
    assert ob.get_best_bid() == 0
    #assert ob.getAskVolume() == o.qty

def test_bid_order(ob):
    o = Bid(10000, 940, 'Bob')
    ts, oib = ob.process_order(o)
    assert len(ts) == 0
    assert oib.qty == o.qty 
    assert oib.price == o.price
    assert oib.trader_id == o.trader_id
    assert oib.timestamp is not None
    assert oib.order_id is not None
    assert ob.get_best_bid() == o.price
    assert ob.get_best_ask() == 0
    #assert ob.getBidVolume() == o.qty

def test_order_invalid_qty(ob):
    o = Bid(0, 940, 'Bob')
    with pytest.raises(OrderQuantityError):
        ts, oib = ob.process_order(o)

def test_order_invalid_price(ob):
    o = Bid(10, 0, 'Bob')
    with pytest.raises(OrderPriceError):
        ts, oib = ob.process_order(o)

def test_matching_bids(ob):
    ts, oib = ob.process_order(Ask(5, 960, 'Alice'))
    assert len(ts) == 0
    assert oib.qty == 5
    assert oib.price == 960
    assert ob.get_best_ask() == 960
    assert ob.get_best_bid() == 0 
    ts, oib = ob.process_order(Bid(2, 960, 'Bob'))
    assert len(ts) == 1
    assert oib is None
    assert ob.get_best_ask() == 960
    assert ob.get_best_bid() == 0 
    ts, oib = ob.process_order(Bid(2, 960, 'Chuck'))
    assert len(ts) == 1
    assert oib is None
    assert ob.get_best_ask() == 960
    assert ob.get_best_bid() == 0 
    ts, oib = ob.process_order(Bid(2, 960, 'Dave'))
    assert len(ts) == 1
    assert oib.qty == 1
    assert oib.price == 960 
    assert ob.get_best_ask() == 0
    assert ob.get_best_bid() == 960 

def test_matching_asks(ob):
    ts, oib = ob.process_order(Bid(5, 960, 'Alice'))
    assert len(ts) == 0
    assert oib.qty == 5
    assert oib.price == 960
    assert ob.get_best_ask() == 0
    assert ob.get_best_bid() == 960
    ts, oib = ob.process_order(Ask(2, 960, 'Bob'))
    assert len(ts) == 1
    assert oib is None
    assert ob.get_best_ask() == 0
    assert ob.get_best_bid() == 960 
    ts, oib = ob.process_order(Ask(2, 960, 'Chuck'))
    assert len(ts) == 1
    assert oib is None
    assert ob.get_best_ask() == 0
    assert ob.get_best_bid() == 960
    ts, oib = ob.process_order(Ask(2, 960, 'Dave'))
    assert len(ts) == 1
    assert oib.qty == 1
    assert oib.price == 960 
    assert ob.get_best_ask() == 960
    assert ob.get_best_bid() == 0 

def test_matching_bid_same_value(ob):
    assert 1

def test_matching_ask_same_value(ob):
    assert 1

def test_incrementing_order_id(ob):
    pass

def test_matching_multitple_asks(testOrderbook):
    assert 1

def test_matching_multiple_bids(testOrderbook):
    assert 1

def test_matching_partial_ask(testOrderbook):
    assert 1

def test_matching_partital_bid(testOrderbook):
    assert 1

def test_matching_multiple_partial_ask(testOrderbook):
    assert 1

def test_matching_multiple_partital_bid(testOrderbook):
    assert 1

def test_exhausting_bid(testOrderbook):
    assert 1

def test_exhausting_ask(testOrderbook):
    '''sell order for whole bid book with extra volume to become a limit sell order'''
    assert 1

def test_many_bids_per_tick(testOrderbook):
    assert 1

def test_many_ticks(testOrderbook):
    assert 1

def test_ask_insufficient_balance(testOrderbook):
    assert 1

def test_bid_insufficient_balance(testOrderbook):
    assert 1

def test_cancel_bid(testOrderbook):
    assert 1

def test_cancel_ask(testOrderbook):
    assert 1

