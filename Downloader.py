from re import S
from unittest import defaultTestLoader
import requests
from io import StringIO
from datetime import datetime as dt, timedelta
import pytz
import pandas as pd
import time
import shutil
import os

from PyQt5.QtCore import QObject, pyqtSignal

class Downloader(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(float)

    def __init__(self, marketlist, path, days):
        super().__init__()
        # Read the CSV file into a DataFrame
        self.marketlist = marketlist
        self.path = path
        self.days = days
        
    def download(self, start, end, timezone, country, exchange, ticker, code):
        tmpresult = []
        try:
            start = str(start)
            end = str(end)
            url = 'https://query1.finance.yahoo.com/v8/finance/chart/'+code+'?interval=1d&period1='+start+'&period2='+end
            res = requests.get(url, headers={'Connection': 'keep-alive',
    'Pragma': 'no-cache', 'Cache-Control': 'no-cache','User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36','Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'})
            data = res.json()
            data1 = {
                'Date': [dt.utcfromtimestamp(ts).strftime('%Y-%m-%d') for ts in data['chart']['result'][0]['timestamp']],
                'Adj Close': data['chart']['result'][0]['indicators']['adjclose'][0]['adjclose'],
                'Volume': data['chart']['result'][0]['indicators']['quote'][0]['volume']
            }
            df = pd.DataFrame(data1)
            for i in range(len(df)):
                date = df.loc[i,'Date']
                close = f"{df.loc[i,'Adj Close']:.4f}"
                vol = f"{df.loc[i,'Volume']:.0f}"
                val = (ticker,close,vol,date)
                tmpresult.append(val)
            return tmpresult
        except Exception as error:
            print(error)
            pass
    
    def delete_all_in_directory(self, directory_path):
        try:
            shutil.rmtree(directory_path)
            os.makedirs(directory_path)  # Recreate the directory if needed
        except Exception as e:
            print(f'Failed to delete {directory_path}. Reason: {e}')
    def downloadData(self):
        df = pd.read_csv(self.marketlist)
        ETF = df[df['MinInvest'] == 0]
        ETF.reset_index(drop=True, inplace=True)

        timezone = 'America/New_York'
        today = dt.now(tz=pytz.timezone(timezone))
        start = str(int((today - timedelta(self.days)).timestamp()))
        end = str(int((today + timedelta(2)).timestamp()))
        print(start)
        print(end)
        self.progress.emit(0)
        self.delete_all_in_directory(self.path)
        for index, row in ETF.iterrows():
            data = self.download(start, end, timezone, 'AU', 'ASX', row['Code'], row['Code']+'.AX')
            data_df = pd.DataFrame(data, columns=['Code','Price','Volume','Date'])
            data_df.to_csv(self.path+'/'+row['Code']+'.csv', index=False)
            print(row['Code'],str(int(index+1))+'/'+str(len(ETF)))
            self.progress.emit(int(index+1)*100/len(ETF))
            time.sleep(0.2)
        self.progress.emit(100)
        self.finished.emit()