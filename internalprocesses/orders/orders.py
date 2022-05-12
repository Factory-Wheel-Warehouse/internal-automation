class Order():

    """
    A class for representing orders.

    Attributes
    ----------
    
    address : Address
        customer address

    customerPO : str
        customer order number
    
    hollander : str
        product number ordered

    qty : int
        qty ordered
    
    price : float
        price per unit

    source : str
        origin (ex. warehouse or specific vendor)

    Methods
    -------

    """

    def __init__(
        self, address, hollander, qty, price,
        customerPO = None
    ):
        self.address = address
        self.customerPO = customerPO
        self.hollander = hollander
        self.qty = qty
        self.price = price
        self.soNum = None
        self.poNum = None
    
    def __str__(self):
        if self.poNum:
            string = f"{self.hollander} x{self.qty} PO #{self.poNum}\n\n"
        else:
            string = f"{self.hollander} x{self.qty} SO #{self.soNum}\n\n"
        string += f"{self.address}"
        return string

    @property
    def customerPO(self): return self._customerPO

    @customerPO.setter
    def customerPO(self, customerPO): self._customerPO = customerPO

    @property
    def hollander(self): return self._hollander

    @hollander.setter
    def hollander(self, hollander): self._hollander = hollander

    @property
    def qty(self): return self._qty

    @qty.setter
    def qty(self, qty): self._qty = qty

    @property
    def price(self): return self._price

    @price.setter
    def price(self, price): self._price = price

    @property
    def soNum(self): return self._soNum

    @soNum.setter
    def soNum(self, soNum): self._soNum = soNum

    @property
    def poNum(self): return self._poNum

    @poNum.setter
    def poNum(self, poNum): self._poNum = poNum

class WalmartOrder(Order):
    
    def __init__(
        self, address, hollander, qty, price,
        customerPO = None
    ):
        super().__init__(
            address, hollander, qty, price,
            customerPO
        )
        self.avenue = "Walmart"

class EbayAlbanyOrder(Order):

    def __init__(
        self, address, hollander, qty, price,
        customerPO = None
    ):
        super().__init__(
            address, hollander, qty, price,
            customerPO
        )
        self.avenue = "Ebay Albany"

class MainEbayOrder(Order):

    def __init__(
        self, address, hollander, qty, price,
        customerPO = None
    ):
        super().__init__(
            address, hollander, qty, price,
            customerPO
        )
        self.avenue = "Main Ebay"

class FacebookOrder(Order):

    def __init__(
        self, address, hollander, qty, price,
        customerPO = None
    ):
        super().__init__(
            address, hollander, qty, price,
            customerPO
        )
        self.avenue = "Facebook"

class AmazonOrder(Order):

    def __init__(
        self, address, hollander, qty, price,
        customerPO = None
    ):
        super().__init__(
            address, hollander, qty, price,
            customerPO
        )
        self.avenue = "Amazon"

class WebsiteOrder(Order):

    def __init__(
        self, address, hollander, qty, price,
        customerPO = None
    ):
        super().__init__(
            address, hollander, qty, price,
            customerPO
        )
        self.avenue = "Website"

class OEDOrder(Order):

    def __init__(
        self, address, hollander, qty, price,
        customerPO = None
    ):
        super().__init__(
            address, hollander, qty, price,
            customerPO
        )
        self.avenue = "OED"
