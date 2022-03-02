class Address():
    
    """
    Class for representing addresses.

    Attributes
    ---------- 
    name : str
        Full name to appear on the address
    street1 : str
        Street address line 1
    city : str
        Address city
    state : str
        Address state
    zipcode : str
        Address zipcode
    street2 : str, optional
        Street address line 2 (Default: None)
    """

    def __init__(self, name, street1, city, state, zipcode, street2 = None):
        self.name = name
        self.street1 = street1
        self.city = city
        self.state = state
        self.zipcode = zipcode
        self.street2 = street2
        self.street = self.street1

    def __str__(self):
        outp = f"{self.name}\n{self.street}\n"
        outp += f"{self.city} {self.state} {self.zipcode}"
        return outp

    @property
    def name(self): return self._name 

    @name.setter
    def name(self, name): self._name = name

    @property
    def street1(self): return self._street1

    @street1.setter
    def street1(self, street1): self._street1 = street1

    @property
    def street2(self): return self._street2

    @street2.setter
    def street2(self, street2): 
        self._street2 = street2
        self.street = f"{self.street1}\n{self.street2}"

    @property
    def city(self): return  self._city

    @city.setter
    def city(self, city): self._city = city

    @property
    def state(self): return self._state

    @state.setter
    def state(self, state): self._state = state

    @property
    def zipcode(self): return self._zipcode

    @zipcode.setter
    def zipcode(self, zipcode): self._zipcode = zipcode