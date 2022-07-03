from orderbook.db_operations import RedisManager


class OrderTree(object):
    def __init__(self, side, base_currency, quote_currency, red):
        self.side = side #used by Order.process_price_level
        self.red = red

        self.KEY_PRICE_TREE = f'prices-{base_currency}-{quote_currency}-{side}'
        self.KEY_TEMPLATE_QUOTE = f'quote-{base_currency}-{quote_currency}-%s'  #quote id
        self.KEY_TEMPLATE_PRICE_QUOTES = f'{side}-{base_currency}-{quote_currency}-%s' #price

    def __len__(self):
        return self.red.zcard(self.KEY_PRICE_TREE)

    def get_price(self, price):
        return self.red.lrange(self.KEY_TEMPLATE_PRICE_QUOTES % price, 0, -1)

    def order_exists(self, order_id):
        #return idNum in self.orderMap
        return self.red.exists(self.KEY_TEMPLATE_QUOTE % order_id)

    def insert_order(self, order):
        price = order.price
        if not self.red.exists(self.KEY_TEMPLATE_PRICE_QUOTES % price):
            self.red.zadd(self.KEY_PRICE_TREE, {price: price})

        self.red.hmset(self.KEY_TEMPLATE_QUOTE % order.order_id, order.__dict__)
        self.red.rpush(self.KEY_TEMPLATE_PRICE_QUOTES % price, order.order_id)

    def update_order_quantity(self, order_id, newQty):
        self.red.hset(self.KEY_TEMPLATE_QUOTE % order_id, 'qty', newQty)


    def remove_order_by_id(self, order_id):
        order = self.red.hgetall(self.KEY_TEMPLATE_QUOTE % order_id)

        self.red.lrem(self.KEY_TEMPLATE_PRICE_QUOTES % order['price'], 0, order_id)
        if not self.red.exists(self.KEY_TEMPLATE_PRICE_QUOTES % order['price']):
            self.red.zrem(self.KEY_PRICE_TREE, order['price'])
        self.red.delete(self.KEY_TEMPLATE_QUOTE % order_id)

    def max_price(self):
        r = self.red.zrevrange(self.KEY_PRICE_TREE, 0, 0)
        return float(r[0]) if r else 0


    def min_price(self):
        r = self.red.zrange(self.KEY_PRICE_TREE, 0, 0)
        return float(r[0]) if r else 0


    def max_price_list(self):
        pipe = self.red.pipeline()
        for order in self.red.lrange(self.KEY_TEMPLATE_PRICE_QUOTES % self.max_price(), 0, -1):
            pipe.hgetall(self.KEY_TEMPLATE_QUOTE % order)
        return pipe.execute()

    def min_price_list(self):
        pipe = self.red.pipeline()
        for order in self.red.lrange(self.KEY_TEMPLATE_PRICE_QUOTES % self.min_price(), 0, -1):
            pipe.hgetall(self.KEY_TEMPLATE_QUOTE % order)
        return pipe.execute()

    def get_quotes(self, reverse=False, depth=10):
        r = []
        opp = self.red.zrevrange if reverse else self.red.zrange


        pipe = self.red.pipeline()
        for price in opp(self.KEY_PRICE_TREE, 0, -1):
            if depth > 0:
                depth -= 1
            else:
                break
            for order in self.red.lrange(self.KEY_TEMPLATE_PRICE_QUOTES % price, 0, -1):
                pipe.hgetall(self.KEY_TEMPLATE_QUOTE % order)
        r += pipe.execute()
        return r


