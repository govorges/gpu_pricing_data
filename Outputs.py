import json

import requests
from bs4 import BeautifulSoup

from os import path
LOCAL_DIR = path.dirname(path.realpath(__file__))

def RetrieveTomsHardwarePerformanceData():
    """Grabs TomsHardware GPU Performance Data and returns a dictionary of gpuName: {1080p Medium: float / 1080p Ultra: float / etc} """
    request = requests.get('https://www.tomshardware.com/reviews/gpu-hierarchy,4388-2.html')
    soup = BeautifulSoup(request.text, 'lxml')

    performance_data = {}
    performance_table = soup.select_one(".table__container > table")

    # Here I'm grabbing the "new" performance table from TomsHardware and 'translating' it to the format of the old one
    request = requests.get("https://www.tomshardware.com/reviews/gpu-hierarchy,4388.html")
    soup = BeautifulSoup(request.text, 'lxml')

    performance_table_new = soup.select_one(".table__container > table")

    for index, table in enumerate([performance_table, performance_table_new]):

        match index:
            case 1:
                dataStructure = { # column index of data
                    "1080p Ultra": 4,
                    "1080p Medium": 3,
                    "1440p Ultra": 5,
                    "4K Ultra": 6
                }
            case _:
                dataStructure = {
                    "1080p Ultra": 1,
                    "1080p Medium": 2,
                    "1440p Ultra": 3,
                    "4K Ultra": 4
                }

        
        for row in table.select("tr"):
            columns = row.select("td")
            if len(columns) < 1:
                continue

            card_name = columns[0].text
            card_name = card_name.replace("GeForce ", "")
            card_name = card_name.replace("Radeon ", "")
            card_name = card_name.replace("Intel ", "")
            
            card_performance_data = {
                "1080p Ultra": columns[
                    dataStructure['1080p Ultra']
                ].text,
                "1080p Medium": columns[
                    dataStructure['1080p Medium']
                ].text,
                "1440p Ultra": columns[
                    dataStructure['1440p Ultra']
                ].text,
                "4K Ultra": columns[
                    dataStructure['4K Ultra']
                ].text
            }

            
            for key in [x for x in card_performance_data.keys()]:
                if "Row" in card_performance_data[key]:
                    card_performance_data.pop(key)
                    continue
                card_performance_data[key] = card_performance_data[key].split(")")[0].split("(")[1].replace("fps", "")
            
            performance_data[card_name] = card_performance_data
        
    return performance_data
        
def GenerateCostPerFrame(pricing_output: dict, performance_data: dict):
    """Takes the output from LoadPricingOutput() & the output from RetrieveTomsHardwarePerformanceData() to create a dictionary of Cost-Per-Frame values"""
    cost_per_frames = {}
    price_data = pricing_output

    for card_name in performance_data.keys():
        if card_name in price_data.keys():
            card_price_mean = price_data[card_name]['price (mean)']
            card_price_low = price_data[card_name]['price (low)']


            cost_per_frames[card_name] = {
                "Cost Per Frames (price (low))": {},
                "price (low)": card_price_low,

                "Cost Per Frames (price (mean))": {},
                "price (mean)": card_price_mean,

                "listings": price_data[card_name]["listings"],
                "performance": performance_data[card_name]
            }
            
            for resolution in performance_data[card_name].keys():
                resolution_performance = performance_data[card_name][resolution]

                cost_per_frames[card_name]["Cost Per Frames (price (low))"][resolution] = round(card_price_low / float(resolution_performance), 2)
                cost_per_frames[card_name]["Cost Per Frames (price (mean))"][resolution] = round(card_price_mean / float(resolution_performance), 2)
    return cost_per_frames

def GenerateCostPerFrameForVendor(vendor: str): 
    pricing_output_filepath = path.join(LOCAL_DIR, "output", f"{vendor}.json")
    pricing_output = json.loads(open(pricing_output_filepath).read())

    performance_data = RetrieveTomsHardwarePerformanceData()

    cost_per_frame_output_filepath = path.join(LOCAL_DIR, "output", f"cost_per_frames_{vendor}.json")
    with open(cost_per_frame_output_filepath, "w+") as outputFile:
        outputFile.write(json.dumps(GenerateCostPerFrame(
            pricing_output = pricing_output,
            performance_data = performance_data
        ), indent=4, sort_keys=False))

def PrettyPrintCostPerFramesForVendor(vendor: str, type: str = "mean"):
    if type not in ['mean', 'low']:
        raise ValueError('arg \'type\' must be either \'mean\' or \'low\'')
    
    cost_per_frame_filepath = path.join(LOCAL_DIR, "output", f"cost_per_frames_{vendor}.json")
    cost_per_frames = json.loads(open(cost_per_frame_filepath).read())

    resolutions = [x for x in [y for y in cost_per_frames.items()][0][1]['performance'].keys()]
    for resolution in resolutions:
        resolution_cost_per_frames = cost_per_frames.copy()
        for item in cost_per_frames.keys():
            if cost_per_frames[item]['performance'].get(resolution) is None:
                resolution_cost_per_frames.pop(item)
        
        resolution_cost_per_frames = sorted(resolution_cost_per_frames.items(), key=lambda x: x[1][f'Cost Per Frames (price ({type}))'][resolution])
        print(f"\n\n{resolution} - {vendor.replace('_', ' ').upper()} ({type} price)")
        for item in resolution_cost_per_frames:
            format_string = f"${format(item[1][f'Cost Per Frames (price ({type}))'][resolution], '.2f')}/frame @ ${item[1][f'price ({type})']}"
            print(f"{item[0]:<22} | " + f"{format_string:<30}" + f"| {item[1]['performance'][resolution]}FPS")

if __name__ == "__main__":
    # vendor str should be a vendor's "identifier".
    # this function requires output data to exist for the provided vendor
    GenerateCostPerFrameForVendor("uk_ebay")
    PrettyPrintCostPerFramesForVendor("uk_ebay")