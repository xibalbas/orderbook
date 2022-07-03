"""
Redis based Limit Order Book.

derived from https://github.com/ab24v07/PyLOB
"""
import math, time
from io import StringIO

from orderbook.redisOrderTree import OrderTree

__all__ = ['OrderException', 'OrderQuantityError', 'OrderPriceError', 'Bid', 'Ask', 'Trade', 'OrderBook']

class OrderException(Exception): pass
class OrderQuantityError(OrderException): pass
class OrderPriceError(OrderException): pass

class Order(object):
    def __init__(self, qty, price, trader_id, timestamp, order_id):
        self.qty = float(qty)
        self.price = float(price)
        self.trader_id = trader_id
        self.timestamp = timestamp
        self.order_id = order_id

    def process_price_level(self, book, tree, orderlist, qty_to_trade):
        '''
        Takes an price level order list and an incoming order and matches
        appropriate trades given the orders quantity.
        '''
        trades = []
        for order in orderlist:
            if qty_to_trade <= 0:
                break
            if qty_to_trade < order.qty:
                traded_qty = qty_to_trade
                # Amend book order
                new_book_qty = order.qty - qty_to_trade
                tree.update_order_quantity(order.order_id, new_book_qty)
                # Incoming done with
                qty_to_trade = 0
            elif qty_to_trade == order.qty:
                traded_qty = qty_to_trade
                # hit bid or lift ask
                tree.remove_order_by_id(order.order_id)
                # Incoming done with
                qty_to_trade = 0
            else:
                traded_qty = order.qty
                # hit bid or lift ask
                tree.remove_order_by_id(order.order_id)
                # continue processing volume at this price
                qty_to_trade -= traded_qty

            transaction_record = {'timestamp': book.get_timestamp(), 'price': order.price, 'qty': traded_qty}
            if tree.side == 'bid':
                transaction_record['party1'] = [order.trader_id, 'bid', order.order_id]
                transaction_record['party2'] = [self.trader_id, 'ask', None]
            else:
                transaction_record['party1'] = [order.trader_id, 'ask', order.order_id]
                transaction_record['party2'] = [self.trader_id, 'bid', None]
            trades.append(transaction_record)
        return qty_to_trade, trades

    def __str__(self):
        return "%s\t@\t%s\tts=%s\ttid=%s\toid=%s" % (self.qty, self.price, self.timestamp, self.trader_id, self.order_id)

    def __repr__(self):
        return '<%s %s @ %s tr:%s o:%s ti:%s>' % (getattr(self, 'side', 'order').capitalize(), self.qty, self.price,
                                                  self.trader_id, self.order_id, self.timestamp)


class Bid(Order):
    def __init__(self, qty, price, trader_id, timestamp=None, order_id=None):
        Order.__init__(self, qty, price, trader_id, timestamp, order_id)
        self.side = 'bid'

    def limit_order(self, book, bids, asks):
        trades = []
        order_in_book = None
        qty_to_trade = self.qty
        while (asks and self.price >= asks.min_price() and qty_to_trade > 0):
            best_price_asks = [Ask(x['qty'], x['price'], x['trader_id'], x['timestamp'], x['order_id']) for x in asks.min_price_list()]
            qty_to_trade, new_trades = self.process_price_level(book, asks, best_price_asks, qty_to_trade)
            trades += new_trades
        # If volume remains, add to book
        if qty_to_trade > 0:
            self.order_id = book.get_next_quote_id()
            self.qty = qty_to_trade
            bids.insert_order(self)
            order_in_book = self
        return trades, order_in_book

    def market_order(self, book, bids, asks):
        trades = []
        qty_to_trade = self.qty
        while qty_to_trade > 0 and self.asks:
            best_price_asks = [Ask(x['qty'], x['price'], x['trader_id'], x['timestamp'], x['order_id']) for x in asks.min_price_list()]
            qty_to_trade, new_trades = self.process_price_level(book, asks, best_price_asks, qty_to_trade)
            trades += new_trades
        return trades


class Ask(Order):
    def __init__(self, qty, price, trader_id, timestamp=None, order_id=None):
        Order.__init__(self, qty, price, trader_id, timestamp, order_id)
        self.side = 'ask'

    def limit_order(self, book, bids, asks):
        trades = []
        order_in_book = None
        qty_to_trade = self.qty
        while (bids and self.price <= bids.max_price() and qty_to_trade > 0):
            best_price_bids = [Bid(x['qty'], x['price'], x['trader_id'], x['timestamp'], x['order_id']) for x in bids.max_price_list()]
            qty_to_trade, new_trades = self.process_price_level(book, bids, best_price_bids, qty_to_trade)
            trades += new_trades
        # If volume remains, add to book
        if qty_to_trade > 0:
            self.order_id = book.get_next_quote_id()
            self.qty = qty_to_trade
            asks.insert_order(self)
            order_in_book = self
        return trades, order_in_book

    def market_order(self, book, bids, asks):
        trades = []
        qty_to_trade = self.qty
        while qty_to_trade > 0 and self.bids:
            best_price_bids = [Bid(x['qty'], x['price'], x['trader_id'], x['timestamp'], x['order_id']) for x in bids.max_price_list()]
            qty_to_trade, new_trades = self.process_price_level(book, bids, best_price_bids, qty_to_trade)
            trades += new_trades
        return trades


class Trade(object):
    def __init__(self, qty, price, timestamp,
                 p1_trader_id, p1_side, p1_order_id,
                 p2_trader_id, p2_side, p2_order_id):
        self.qty = qty
        self.price = price
        self.timestamp = timestamp
        self.p1_trader_id = p1_trader_id
        self.p1_side = p1_side
        self.p1_order_id = p1_order_id
        self.p2_trader_id = p2_trader_id
        self.p2_side = p2_side
        self.p2_order_id = p2_order_id


class OrderBook(object):
    def __init__(self, base_currency, quote_currency, red, tick_size=0.0001):
        self.red = red
        self.tick_size = tick_size

        self.tape = []# deque(maxlen=None) # Index [0] is most recent trade
        self.bids = OrderTree('bid', base_currency, quote_currency, red)
        self.asks = OrderTree('ask', base_currency, quote_currency, red)

        self._last_timestamp = None
        self.KEY_COUNTER_ORDER_ID = 'counter:%s-%s-order_id' % (base_currency, quote_currency)

    def process_order(self, order):
        order_in_book = None

        if order.qty <= 0:
            raise OrderQuantityError('order.qty must be > 0')

        if order.price <= 0:
            raise OrderPriceError('order.price must be > 0')

        order.timestamp = self.get_timestamp()

        #order['price'] = self._clip_price(order['price'])
        trades, order_in_book = order.limit_order(self, self.bids, self.asks)

        return trades, order_in_book

    def cancel_order(self, side, order_id):
        if side == 'bid':
            self.bids.remove_order_by_id(order_id)
        elif side == 'ask':
            self.asks.remove_order_by_id(order_id)

    def get_best_bid(self):
        return float(self.bids.max_price())

    def get_worst_bid(self):
        return self.bids.min_price()

    def get_best_ask(self):
        return self.asks.min_price()

    def get_worst_ask(self):
        return self.asks.max_price()

    def _clip_price(self, price):
        """ Clips the price according to the tick_size """
        return round(price, int(math.log10(1 / self.tick_size)))

    def get_timestamp(self):
        t = time.time()
        while t == self._last_timestamp:
            t = time.time()
        self._last_timestamp = t
        return t

    def get_next_quote_id(self):
        return self.red.incr(self.KEY_COUNTER_ORDER_ID) #defaults to 1 if not present

    def __str__(self):
        fileStr = StringIO()
        #fileStr.write('Bid vol: %s Ask vol: %s\n' % (self.bids.volume, self.asks.volume))
        #fileStr.write('Bid count: %s Ask count: %s\n' % (self.bids.nOrders, self.asks.nOrders))
        #fileStr.write('Bid depth: %s Ask depth: %s\n' % (self.bids.lobDepth, self.asks.lobDepth))
        fileStr.write('Bid max: %s Ask max: %s\n' % (self.bids.max_price(), self.asks.max_price()))
        fileStr.write('Bid min: %s Ask min: %s\n' % (self.bids.min_price(), self.asks.min_price()))
        fileStr.write("------ Bids -------\n")
        if self.bids != None and len(self.bids) > 0:
            for v in self.bids.get_quotes(reverse=True): #priceTree.items(reverse=True):
                fileStr.write('%s @ %s\n' % (float(v['qty'])/1e5, float(v['price'])/1e8))
        fileStr.write("\n------ Asks -------\n")
        if self.asks != None and len(self.asks) > 0:
            for v in self.asks.get_quotes(): #priceTree.items():
                #fileStr.write('%s\n' % v)
                fileStr.write('%s @ %s\n' % (float(v['qty'])/1e5, float(v['price'])/1e8))
        fileStr.write("\n------ Trades ------\n")
        if self.tape != None and len(self.tape) > 0:
            for entry in self.tape[-5:]:
                fileStr.write(str(entry['qty']) + " @ " + str(entry['price']) + " (" + str(entry['timestamp']) + ")\n")
        fileStr.write("\n")
        return fileStr.getvalue()

