from logging import root
import pandas as pd
import os
import numpy as np
import cvxpy as cp
from PyQt5.QtCore import QObject, pyqtSignal

class Analyser(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(float)
    finalList = pyqtSignal(list)
    
    def __init__(self, root_path, path, pick_num, balance, sortby):
        super().__init__()
        # Read the CSV file into a DataFrame
        self.root_path = root_path
        self.path = path
        self.pick_num = pick_num
        self.balance = balance
        self.sortby = sortby
        
    def getChanges(self, df, period, periodType = 'M'):
        if periodType == 'D':
            data = df.tail(1*period+1)
        if periodType == 'W':
            data = df.tail(5*period+1)
        if periodType == 'M':
            data = df.tail(21*period+1)
        chg = (data['Price'].iloc[-1] - data['Price'].iloc[0])*100/data['Price'].iloc[0]
        return round(chg,4)

    def getMaxDown(self, df, days):
        data = df.tail(days)
        data.reset_index(drop=True, inplace=True)
        minVal = 999999
        maxVal = 0
        day_h = 0
        day_l = 0
        result = []
        for index, row in data.iterrows():
            price = row['Price']
            if price > maxVal:
                if index > day_h:
                    result.append([(minVal-maxVal)*100/maxVal,day_l-day_h,index-day_h])
                maxVal = price
                minVal = maxVal
                day_h = index
                day_l = index
            elif price < minVal:
                minVal = price
                day_l = index
        result.append([(minVal-maxVal)*100/maxVal,day_l-day_h,len(data)-day_h-1])
        array = np.array(result)
        sorted_array = array[array[:, 0].argsort()]
        worst = [0,0,0]
        VaR = [0,0,0]
        if len(sorted_array) > 0:
            percentile_index = int(0.2 * len(sorted_array))
            if percentile_index >= 0 and percentile_index < len(sorted_array):
                VaR = [sorted_array[percentile_index][0],sorted_array[percentile_index][1],sorted_array[percentile_index][2]]
            worst = [sorted_array[0][0],sorted_array[0][1],sorted_array[0][2]]
        return worst,VaR

    def getStd(self, df, days):
        df['chg'] = df['Price'].diff()
        return df.tail(days)['chg'].std()

    def getAvgVol(self, df, days):
        return int(df.tail(days)['Volume'].mean(numeric_only=True))

    def analyse(self, df):
        price = df.tail(1).iloc[0]['Price']
        D1 = self.getChanges(df, 1, 'D')
        W1 = self.getChanges(df, 1, 'W')
        M1 = self.getChanges(df, 1)
        M3 = self.getChanges(df, 3)
        M6 = self.getChanges(df, 6)
        M12 = self.getChanges(df, 12)
        std = self.getStd(df, 3*21)
        vol = self.getAvgVol(df, 3*21)
        worst, VaR = self.getMaxDown(df, 3*21)
        return [price,vol,D1,W1,M1,M3,M6,M12,std,worst[0],worst[1],worst[2],VaR[0],VaR[1],VaR[2]]


    def getWeightBasedOnRisk(self, std, returns):
        data = {'std':std,'return': returns}
        df = pd.DataFrame(data)

        # Calculate the covariance matrix from the standard deviations
        cov_matrix = np.diag(df['std'] ** 2)

        # Number of assets
        num_assets = len(df)

        # Define the variables
        weights = cp.Variable(num_assets)
        size = len(std)

        # Define the objective function (minimize portfolio variance)
        portfolio_variance = cp.quad_form(weights, cov_matrix)
        objective = cp.Minimize(portfolio_variance)

        # Define the constraints
        constraints = [
            cp.sum(weights) == 1,  # Sum of weights equals 1
            weights >= round(1.0/(size*2.5),2)           # Non-negativity constraint on weights
        ]

        # Solve the optimization problem
        problem = cp.Problem(objective, constraints)
        problem.solve()

        # Get the optimal weights
        optimal_weights = weights.value.tolist()
        return optimal_weights

    def floor_to_hundred(self, number):
        return (number // 100) * 100

    def startAnalyse(self):
        result = []
        self.progress.emit(0)
        details = pd.read_csv(self.root_path+'/Funds.csv')
        i=1
        length = len(os.listdir(self.path))
        for filename in os.listdir(self.path):
            if filename.endswith('.csv'):
                file_path = os.path.join(self.path, filename)       
                # Read the CSV file into a DataFrame
                df = pd.read_csv(file_path).dropna(subset=['Price'])
                ticker = os.path.splitext(filename)[0]
                detail = details[details['Code']==ticker].iloc[0]
                try:
                    r = self.analyse(df)
                    result.append([ticker,detail[0],detail[3],round(detail[4]/1000000,2),detail[10]]+r)
                except Exception as error:
                    pass
            self.progress.emit(int(i)*100/length)
            i = i + 1
        
        data_df = pd.DataFrame(result, columns=['Code','Name','Sector','Market Cap','Mgt Fee','Price','Avg Volume','1D','1W','1M','3M','6M','12M','Std','Max Drawdown','Max Drawdown Duration','Drawdown Recovered Duration','80% Drawdown','80% Drawdown Duration','80% Drawdown Recovered Duration'])
        df_sorted = data_df.sort_values(by='3M', ascending=False)
        df_sorted.to_csv(self.root_path+'/result.csv', index=False)
 
        # Filter based on the conditions
        df_filtered = df_sorted[(df_sorted['Market Cap'] > 20 ) &
                                (df_sorted['Avg Volume'] > 5000 ) &
                                (df_sorted['Max Drawdown'] > -10 ) &
                                (df_sorted['80% Drawdown'] > -3 ) &
                                (df_sorted['Max Drawdown Duration'] < 10 ) &
                                (df_sorted['80% Drawdown Duration'] < 3 ) &
                                (df_sorted['1M'] > 1 ) &
                                (df_sorted['3M'] > 5 ) &
                                (df_sorted['6M'] > 10)]

        selected_num = self.pick_num
        balance = self.balance

        selected=df_filtered.sort_values(by=self.sortby, ascending=False).head(selected_num)
        selected.reset_index(drop=True, inplace=True)
        std = selected['Std'].tolist()
        returns = selected['3M'].tolist()
        
        weights_risk = self.getWeightBasedOnRisk(std, returns)

        final_result = []
        for index, row in selected.iterrows():
            final_result.append([row['Code'],row['Sector'],f"${row['Price']:.2f}",f"{weights_risk[index]*100:.2f}%",f"${self.floor_to_hundred(balance*weights_risk[index]):.2f}",f"{self.floor_to_hundred(balance*weights_risk[index])/row['Price']:.0f}",f"{row['1M']:.2f}%",f"{row['3M']:.2f}%",f"{row['6M']:.2f}%",f"{row['12M']:.2f}%",f"{row['Max Drawdown']:.2f}%",f"{row['80% Drawdown']:.2f}%",f"{row['Market Cap']:.2f}M",f"{row['Avg Volume']:.0f}",f"{row['Mgt Fee']:.2f}%"])
        
        self.progress.emit(100)
        self.finalList.emit(final_result)
        self.finished.emit()
