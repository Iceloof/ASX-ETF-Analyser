import requests
import json
import urllib.parse
import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal

class MarketListDownloader(QObject):
    
    finished = pyqtSignal()

    def __init__(self, path):
        super().__init__()
        # URL to send the GET request to
        page = 1
        pageSize = 25
        base_url = 'https://digitalfundservice.feprecisionplus.com/FundDataService.svc/GetUnitList?jsonString='
        ids = '%2C'.join(str(i) for i in range(1, 514))
        param = '%7B%22FilteringOptions%22%3A%7B%22undefined%22%3A0%2C%22Ter%22%3A%7B%7D%2C%22Amc%22%3A%7B%7D%2C%22RangeId%22%3A17200467%2C%22RangeName%22%3A%22tpp44395%22%2C%22CategoryId%22%3Anull%2C%22Category2Id%22%3Anull%2C%22PriipProductCode%22%3Anull%2C%22DefaultCategoryId%22%3Anull%2C%22DefaultCategory2Id%22%3Anull%2C%22ForSaleIn%22%3Anull%2C%22ShowMainUnits%22%3Afalse%2C%22MPCategoryCode%22%3Anull%7D%2C%22ProjectName%22%3A%22tpp%22%2C%22LanguageCode%22%3A%22en-au%22%2C%22UserType%22%3A%22%22%2C%22Region%22%3A%22%22%2C%22LanguageId%22%3A%221%22%2C%22Theme%22%3A%22tpp44395%22%2C%22SortingStyle%22%3A%221%22%2C%22PageNo%22%3A1%2C%22PageSize%22%3A125%2C%22OrderBy%22%3A%22UnitName%3Ainit%22%2C%22IsAscOrder%22%3Atrue%2C%22OverrideDocumentCountryCode%22%3Anull%2C%22ToolId%22%3A%221%22%2C%22PrefetchPages%22%3A80%2C%22PrefetchPageStart%22%3A1%2C%22OverridenThemeName%22%3A%22tpp44395%22%2C%22ForSaleIn%22%3A%22%22%2C%22ValidateFeResearchAccess%22%3Afalse%2C%22HasFeResearchFullAccess%22%3Afalse%2C%22EnableSedolSearch%22%3A%22false%22%2C%22RowCount%22%3A513%2C%22RowIDs%22%3A%22'+ids+'%22%7D'
        self.full_url = f"{base_url}{param}"
        self.path = path

    def download(self):
        try:
            print("Started updating ...")
            # Send the GET request
            response = requests.get(self.full_url, timeout=300)

            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                data = json.loads(response.json())
                dataList = data['DataList']
            else:
                print(f"Failed to retrieve data: {response.status_code}")
    
            finalList = []
            for item in dataList:
                if item['Charges']['MinInvestment'] is None:
                    minInv = 0
                else:
                    minInv = item['Charges']['MinInvestment']['Amount']
                if item['FundInfo']['FundSize'] is None:
                    fundSize = 0
                else:
                    fundSize = item['FundInfo']['FundSize']['Amount']
                d = [item['Price']['Name'],item['Price']['FundCode_Customtable'],item['Price']['Price']['Amount'],item['FundInfo']['Sector'],fundSize,item['FundInfo']['FundLaunchDate'],item['Risk'],item['Ratings'],minInv,item['Charges']['InitialCharge'],item['Charges']['AMC']]
                finalList.append(d)

            df = pd.DataFrame(finalList, columns=['Name', 'Code','Price','Sector','FundSize','FundLaunchDate','Risk','Ratings','MinInvest','InitialCharge','AMC'])

            df.to_csv(self.path, index=False)
            print("Market List Updated ", self.path)
        except:
            pass
        self.finished.emit()