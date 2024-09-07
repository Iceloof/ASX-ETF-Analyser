import select
import sys
import os
import tempfile
import requests
from turtle import right
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox, QProgressBar, QTableWidget, QTableWidgetItem, QSpinBox, QAbstractItemView
from PyQt5.QtCore import QThread, Qt
from PyQt5.QtGui import QIcon, QPixmap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pandas as pd
from MarketListDownloader import MarketListDownloader
from Downloader import Downloader
from Analyser import Analyser
import warnings

class ChartPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(640,320)
        self.layout = QVBoxLayout(self)
        self.chart_label = QLabel("")
        self.layout.addWidget(self.chart_label)

    def plot_chart(self, data, ticker, path):
        # Clear the existing chart
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        fig = plt.figure(figsize=(8, 2))
        self.axes = fig.add_subplot(111)
        fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.22)
        plt.plot(data['Date'], data['Price'])
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.xticks(rotation=20)
        plt.title(ticker+' Historical Prices')
   
        canvas = FigureCanvas(fig)
        self.layout.addWidget(canvas)
        
class MainWindow(QMainWindow):
    def  __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        temp_dir = tempfile.gettempdir()
        # Define the new folder name
        root_folder = "ASXTempData"
        history_folder = "history"
        # Create the full path for the new folder
        self.root_folder_path = os.path.join(temp_dir, root_folder)
        self.history_folder_path = os.path.join(temp_dir, root_folder, history_folder)
        
        self.icon_path = self.root_folder_path+'/logo.png'
        self.icon_url = 'https://www.iceloof.com/logo192.png'
        
        self.setWindowTitle("ASX Stock Market Analyzer")
        # Check if the icon file exists
        if os.path.exists(self.icon_path):
            self.set_window_icon(self.icon_path)
        else:
            self.download_icon(self.icon_url, self.icon_path)
        self.resize(640, 560)  # Set the window size to 1024x720

        # Create the main vertical layout
        main_layout = QVBoxLayout()

        # Create the first horizontal layout for the first row
        first_row_layout = QHBoxLayout()
        self.market_list_button = QPushButton("Update Market List")
        self.market_list_button.clicked.connect(self.update_market_list)
        first_row_layout.addWidget(self.market_list_button)

        self.historical_data_button = QPushButton("Download Historical Data")
        self.historical_data_button.clicked.connect(self.download_historical_data)
        first_row_layout.addWidget(self.historical_data_button)

        self.period_label = QLabel("Select Period:")
        first_row_layout.addWidget(self.period_label)
        self.period_selection = QComboBox()
        self.period_selection.addItems(["1 Month", "3 Months", "6 Months", "1 Year", "2 Years", "3 Years", "5 Years"])
        self.period_selection.setCurrentText("1 Year")
        first_row_layout.addWidget(self.period_selection)

        main_layout.addLayout(first_row_layout)

        second_row_layout = QHBoxLayout()
        self.stock_pick_label = QLabel("Number of Stocks to Pick:")
        second_row_layout.addWidget(self.stock_pick_label)
        self.stock_pick_number = QSpinBox()
        self.stock_pick_number.setRange(1, 100)
        self.stock_pick_number.setValue(4)
        second_row_layout.addWidget(self.stock_pick_number)

        self.sort_column_label = QLabel("Sort By Column:")
        second_row_layout.addWidget(self.sort_column_label)
        self.sort_column_selection = QComboBox()
        self.sort_column_selection.addItems(["1M", "3M", "6M", "12M", "Std", "Avg Volume", "Market Cap", "Max Drawdown", "80% Drawdown"])
        self.sort_column_selection.setCurrentText("6M")
        second_row_layout.addWidget(self.sort_column_selection)

        self.initial_balance_label = QLabel("Initial Balance:")
        second_row_layout.addWidget(self.initial_balance_label)
        self.initial_balance_input = QSpinBox()
        self.initial_balance_input.setRange(1, 1000000000)
        self.initial_balance_input.setValue(80000)
        second_row_layout.addWidget(self.initial_balance_input)

        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.clicked.connect(self.analyze_data)
        second_row_layout.addWidget(self.analyze_button)
        
        main_layout.addLayout(second_row_layout)
        
        # Progress Bar
        self.progress_label = QLabel("Progress:")
        main_layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("%.0f%%")  # Display percentage with 2 decimal places
        main_layout.addWidget(self.progress_bar)

        # Results Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(15)
        self.results_table.setFixedHeight(160)
        self.results_table.setHorizontalHeaderLabels(["Ticker", "Sector", "Price", "Weight", "Amount", "QTY", "1M", "3M", "6M", "1Y", "Max Drawdown", "80% Drawdown", "Market Cap", "Avg Vol", "Mgt Fee"])
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Connect the selection change signal to the function
        self.results_table.itemSelectionChanged.connect(self.select_result_row)
        main_layout.addWidget(self.results_table)

        self.chart_panel = ChartPanel()
        main_layout.addWidget(self.chart_panel)
        
        # Set the layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        # Create the new folder
        try:
            os.mkdir(self.root_folder_path)
            print(f"Folder created at: {self.root_folder_path}")
        except FileExistsError:
            print(f"Folder already exists at: {self.root_folder_path}")
        try:
            os.mkdir(self.history_folder_path)
            print(f"Folder created at: {self.history_folder_path}")
        except FileExistsError:
            print(f"Folder already exists at: {self.history_folder_path}")
    
    def closeEvent(self, event):
        event.accept()
        QApplication.instance().quit()
      
    def set_window_icon(self, path):
        pixmap = QPixmap(path)
        self.setWindowIcon(QIcon(pixmap))
    
    def download_icon(self, url, path):
        response = requests.get(url)
        if response.status_code == 200:
            with open(path, 'wb') as file:
                file.write(response.content)
            self.set_window_icon(path)
        else:
            print("Failed to download the icon")
        
    def select_result_row(self):
        selected_item = self.results_table.selectedItems()
        if selected_item:
            ticker = selected_item[0].text()
            data = pd.read_csv(self.history_folder_path+'/'+ticker+'.csv')
            data['Date'] = pd.to_datetime(data['Date'])
            self.chart_panel.plot_chart(data.tail(252), ticker, self.root_folder_path)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{value:.2f}%")
        
    def update_Table(self, data):
        length = len(data)
        for i in range(length):
            self.results_table.setRowCount(i+1)
            for column in range(15):
                item = QTableWidgetItem(data[i][column])
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Make item non-editable
                if column >= 1:  # Align text to the right from the second column onwards
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.results_table.setItem(i, column, item)
        # Automatically adjust the width of the columns to fit the contents
        self.results_table.resizeColumnsToContents()
        
    def update_market_list(self):
        # Disable the button and update text
        self.market_list_button.setEnabled(False)
        self.market_list_button.setText("Updating...")

        # Create a QThread object
        self.thread = QThread()
        # Create a MarketListDownloader object
        self.market_list_downloader = MarketListDownloader(self.root_folder_path+'/Funds.csv')
        # Move the MarketListDownloader object to the thread
        self.market_list_downloader.moveToThread(self.thread)
        # Connect signals and slots
        self.thread.started.connect(self.market_list_downloader.download)
        self.market_list_downloader.finished.connect(self.thread.quit)
        self.market_list_downloader.finished.connect(self.market_list_downloader.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Re-enable the button and reset text when done
        self.thread.finished.connect(lambda: self.market_list_button.setEnabled(True))
        self.thread.finished.connect(lambda: self.market_list_button.setText("Update Market List"))        
        # Start the thread
        self.thread.start()

    def download_historical_data(self):
        # Disable the button and update text
        self.historical_data_button.setEnabled(False)
        self.historical_data_button.setText("Downloading ...")
        
        selected_period = self.period_selection.currentText()
        days = 365
        if selected_period == "1 Month":
            days = 31
        elif selected_period == "3 Months":
            days = 62
        elif selected_period == "6 Months":
            days = 93
        elif selected_period == "1 Year":
            days = 366
        elif selected_period == "2 Years":
            days = 366*2
        elif selected_period == "3 Years":
            days = 366*3
        elif selected_period == "5 Years":
            days = 366*5

        # Create a QThread object
        self.thread1 = QThread()
        # Create a Downloader object
        self.downloader = Downloader(self.root_folder_path+'/Funds.csv', self.history_folder_path, days)
        # Move the MarketListDownloader object to the thread
        self.downloader.moveToThread(self.thread1)
        # Connect signals and slots
        self.thread1.started.connect(self.downloader.downloadData)
        self.downloader.finished.connect(self.thread1.quit)
        self.downloader.finished.connect(self.downloader.deleteLater)
        self.thread1.finished.connect(self.thread1.deleteLater)
        self.downloader.progress.connect(self.update_progress)
        
        # Re-enable the button and reset text when done
        self.thread1.finished.connect(lambda: self.historical_data_button.setEnabled(True))
        self.thread1.finished.connect(lambda: self.historical_data_button.setText("Download Historical Data"))        
        # Start the thread
        self.thread1.start()

    def analyze_data(self):

        # Disable the button and update text
        self.analyze_button.setEnabled(False)
        self.analyze_button.setText("Analyzing ...")
        
        # Create a QThread object
        self.thread2 = QThread()
        # Create a Downloader object
        self.analyser = Analyser(self.root_folder_path, self.history_folder_path, self.stock_pick_number.value(), self.initial_balance_input.value(), self.sort_column_selection.currentText())
        # Move the MarketListDownloader object to the thread
        self.analyser.moveToThread(self.thread2)
        # Connect signals and slots
        self.thread2.started.connect(self.analyser.startAnalyse)
        self.analyser.finished.connect(self.thread2.quit)
        self.analyser.finished.connect(self.analyser.deleteLater)
        self.thread2.finished.connect(self.thread2.deleteLater)
        self.analyser.progress.connect(self.update_progress)
        self.analyser.finalList.connect(self.update_Table)
        
        # Re-enable the button and reset text when done
        self.thread2.finished.connect(lambda: self.analyze_button.setEnabled(True))
        self.thread2.finished.connect(lambda: self.analyze_button.setText("Analyzer"))        
        # Start the thread
        self.thread2.start()
        
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
