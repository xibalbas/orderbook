import math, time
from os import stat
from io import StringIO
from orderbook.redisOrderTree import OrderTree
from orderbook.exceptions import *

__all__ = ['OrderException', 'OrderQuantityError', 'OrderPriceError', 'Bid', 'Ask', 'Trade', 'OrderBook']

class Order:
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

            transaction_record = {
                'timestamp': book.get_timestamp(),
                'price': order.price,
                'qty': traded_qty
                }
            if tree.side == 'bid':                
                transaction_record['bid_side_trader_id'] = order.trader_id
                transaction_record['bid_side_order_id'] = order.order_id
                
                transaction_record['ask_side_trader_id'] = self.trader_id
                transaction_record['ask_side_order_id'] = None
                
            else:                
                transaction_record['bid_side_trader_id'] = self.trader_id
                transaction_record['bid_side_order_id'] = None

                transaction_record['ask_side_trader_id'] = order.trader_id
                transaction_record['ask_side_order_id'] = order.order_id
                
            Trade(transaction=transaction_record)
                   
            trades.append(transaction_record)
            
        return qty_to_trade, trades

    def __str__(self):
        return f"{self.qty}\t@\t{self.price}\tts={self.timestamp}\ttid={self.trader_id}\toid={self.order_id}"

    def __repr__(self):
        return f"<{getattr(self, 'side', 'order').capitalize()} {self.qty} @ {self.price} tr:{self.trader_id} o:{self.order_id} ti:{self.timestamp}>" 


class Bid(Order):
    def __init__(self, qty, price, trader_id, timestamp=None, order_id=None):
        Order.__init__(self, qty, price, trader_id, timestamp, order_id)
        self.side = 'bid'

    def limit_order(self, book, bids, asks):
        trades = []
        order_in_book = None
        qty_to_trade = self.qty
        while (asks and self.price >= asks.min_price() and qty_to_trade > 0):
            best_price_asks = [Ask(item['qty'],
                                   item['price'],
                                   item['trader_id'],
                                   item['timestamp'],
                                   item['order_id']) for item in asks.min_price_list()]
            
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
            best_price_asks = [Ask(x['qty'],
                                   x['price'],
                                   x['trader_id'],
                                   x['timestamp'],
                                   x['order_id']) for x in asks.min_price_list()]
            
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
            best_price_bids = [Bid(x['qty'],
                                   x['price'],
                                   x['trader_id'],
                                   x['timestamp'],
                                   x['order_id']) for x in bids.max_price_list()]
            
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
            best_price_bids = [Bid(item['qty'],
                                   item['price'],
                                   item['trader_id'],
                                   item['timestamp'],
                                   item['order_id']) for item in bids.max_price_list()]
            
            qty_to_trade, new_trades = self.process_price_level(book, bids, best_price_bids, qty_to_trade)
            trades += new_trades
        return trades


class Trade:
    def __init__(self, transaction: dict):
        self.qty = transaction.get('qty')
        self.price = transaction.get('price')
        self.timestamp = transaction.get('timestamp')
        
        self.ask_side_trader_id = transaction.get('ask_side_trader_id')
        self.ask_side_order_id = transaction.get('ask_side_order_id')
        
        self.bid_side_trader_id = transaction.get('bid_side_trader_id')
        self.bid_side_order_id = transaction.get('bid_side_order_id')
        
        self.record(transaction=transaction)
        
    def record(self, transaction: dict):
        # should record in db
        # TODO need a SQL model
        pass
    
    @staticmethod
    def get_all_trades():
        # read all trades from db
        pass
    
    @staticmethod
    def get_last_10_trades():
        # read last trades from db
        pass
    
    @staticmethod
    def get_user_trades():
        # get specific user trades
        pass

class OrderBook:
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

        fileStr.write('Bid max: %s Ask max: %s\n' % (self.bids.max_price(), self.asks.max_price()))
        fileStr.write('Bid min: %s Ask min: %s\n' % (self.bids.min_price(), self.asks.min_price()))
        fileStr.write("------ Bids -------\n")
        if self.bids != None and len(self.bids) > 0:
            for v in self.bids.get_quotes(reverse=True):
                fileStr.write(f"{float(v['qty'])} @ {float(v['price'])}\n" )
                
        fileStr.write("\n------ Asks -------\n")
        if self.asks != None and len(self.asks) > 0:
            for v in self.asks.get_quotes(): #priceTree.items():
                fileStr.write("{float(v['qty'])} @ {float(v['price'])}\n")
                
        fileStr.write("\n------ Trades ------\n")
        if self.tape != None and len(self.tape) > 0:
            for entry in self.tape[-5:]:
                fileStr.write(str(entry['qty']) + " @ " + str(entry['price']) + " (" + str(entry['timestamp']) + ")\n")
        fileStr.write("\n")
        return fileStr.getvalue()
    