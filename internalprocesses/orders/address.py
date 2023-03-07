class Address:
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

    def __init__(self, name, street1, city, state, zipcode, street2=None,
                 country='UNITED STATES'):
        self.name = name
        self.street1 = street1
        self.city = city
        self.state = state
        self.zipcode = zipcode
        self.street2 = street2
        self.country = country
        self.street = self.street1

    def __str__(self):
        outp = f"{self.name}\n{self.street}\n"
        outp += f"{self.city} {self.state} {self.zipcode}"
        return outp
