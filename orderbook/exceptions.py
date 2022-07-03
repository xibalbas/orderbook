class OrderException(Exception): 
    pass

class OrderQuantityError(OrderException): 
    pass

class OrderPriceError(OrderException): 
    pass