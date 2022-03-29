import os
import csv
from typing import TYPE_CHECKING, List, Dict

"""
Module containing functions to build our top selling wheels
and check the price we would offer to buy each one
"""

def buildCost(costPath: str) -> Dict[str, float]:
    """
    Builds a part average cost dictionary with the costs capped at 75

    Keyword Arguments:
        costPath: str -- The relative path to the part average cost 
                         csv file
    """
    cd = os.path.dirname(__file__)
    path = os.path.join(cd, costPath)
    with open(path) as csvFile:
        reader = csv.reader(csvFile)
        return(setAverageCost(reader))

def setAverageCost(reader: csv.reader) -> Dict[str, float]:
    """
    Reads in our partAverageCost data to build a dictionary of hollanders
    and their average cost, capped at 75, to serve as a baseline offer

    Keyword Arguments:
        reader: csv.reader -- the csv reader object reading the file

    Returns:
        Dict[str, float] -- A dictionary of hollanders and average costs
    """
    partAverageCost = {}
    for row in reader:
        if row[0][:3] == "ALY":
            cost = float(row[6])
            # Caps prices at 75
            if cost > 75:
                cost = 75.00
            hollander = row[0][3:8]
            if hollander not in partAverageCost:
                partAverageCost[hollander] = cost
            else:
                # Roughly averages multiple occurences of the same 
                # hollander but in different colors
                partAverageCost[hollander] += cost
                partAverageCost[hollander] /= 2
                partAverageCost[hollander] = round(partAverageCost[hollander], 2)
    return partAverageCost

def blackburnsPricingDict(relativePath: str) -> Dict[str, float]:
    """
    Builds a pricing dictionsary for specifically blackburns data

    Keyword Argument:
        relativePath: str -- the relative path to blackburn's buy list

    Returns:
        Dict[str, float] -- a dictionary of hollanders as strings and
                            their price as a float
    """
    blackburnsPricingDict = {}
    cd = os.path.dirname(__file__)
    path = os.path.join(cd, relativePath)
    with open(path) as csvFile:
        reader = csv.reader(csvFile)
        for row in reader:
            if row[3].isdigit():
                hollander = row[1][4:]
                if hollander[-1].isalpha():
                    hollander = hollander[len(hollander) - 1]
                while len(hollander) < 5:
                    hollander = "0" + hollander
                blackburnsPricingDict[hollander] = float(row[3])
    return blackburnsPricingDict

def buildTopSold(ourPath: str, coastPath: str) -> List[str]:
    """
    Builds the top 200 hollanders sold in the form of our top 100
    last quarter and Coast to Coast's top 100 sold.

    Keyword Arguments:
        ourPath: str -- The ralative path to the CSV file containing 
                        our data
        coastPath: str -- the realtive path to the file containing
                          coast to coast's data
        
    Returns:
        list -- a list of top 200 hollanders as strings
    """
    cd = os.path.dirname(__file__)
    path = os.path.join(cd, ourPath)
    with open(path) as csvFile:
        reader = csv.reader(csvFile)
        # Creates a list of [volumeSold, hollander] data sorted by 
        # volumeSold in descending order. The top 100 are then kept
        sortedByVolume = sorted([[int(row[4]), row[1][3:8]] for row in 
                list(reader) if row[1][:3] == "ALY"], reverse = True)[:100]
        topSales = [entry[1] for entry in sortedByVolume]
    path = os.path.join(cd, coastPath)
    with open(path) as csvFile:
        reader = csv.reader(csvFile)
        topSales += [entry[0][3:8] for entry in list(reader)][1:101]
    return topSales

def buildPriceDict() -> Dict[str, float]:
    """
    Uses our average cost per hollander, 200 top sold wheels, and
    Blackburns pricing to build a price list. The price list prioritizes
    blackburns pricing and includes all of the hollanders in blackburns
    buy list.

    Returns:
        Dict[str, float] -- a dictionary of hollanders as strings and
                            their price as a float
    """
    priceDict = {}
    averageCost = buildCost("data/PartAverageCost.csv")
    topSold = buildTopSold("data/salesByVolume.csv", "data/Coast150.csv")
    blackburnsPricing = blackburnsPricingDict("data/BlackburnsPricing.csv")
    # For each hollander check for a price from blackburns, then check
    # for our average cost if not found, then if neither are found set
    # price at -1. (A flag value)
    for hollander in topSold:
        if hollander in blackburnsPricing:
            priceDict[hollander] = blackburnsPricing[hollander]
        elif hollander in averageCost:
            priceDict[hollander] = averageCost[hollander]
        else:
            priceDict[hollander] = -1
    # Add all hollanders on blackburns list that aren't already
    # in the price list and have a price greater than or equal to 20
    for key, value in blackburnsPricing.items():
        if key not in priceDict and value >= 20:
            priceDict[key] = value
    return priceDict

def checkHollander(hollander: str, priceList: dict) -> str:
    """
    A function to get a hollanders price for the list if available.
    If not, "offer $20 as scrap" is returned.

    Keyword Arguments:
        hollander: str -- The hollander to search for
        priceList: dict -- The price list dictionary being used

    Returns:
        str -- The offer as a string
    """
    if hollander in priceList:
        if priceList[hollander] > 0:
            return (hollander + ': Offer ${:.2f}'.format(priceList[hollander])  + '\n')
        else:
            return str(hollander) + ": pricing not available yet\n"
    else:
        return (str(hollander) + ": Offer $20 as scrap\n")