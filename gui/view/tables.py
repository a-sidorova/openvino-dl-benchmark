from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from models.deploy_config import *


class TableModel(QTableWidget):
    def __init__(self):
        super().__init__()
        self._models = []
        self._count_col = 5
        self._count_row = 50
        self._headers = ['Task', 'Name', 'Precision', 'SourceFramework', 'Path']
        self.setColumnCount(self._count_col)
        self.setRowCount(self._count_row)
        self.setHorizontalHeaderLabels(self._headers)
        self.__resize_columns()
        self.clear()

    def __resize_columns(self):
        header = self.horizontalHeader()
        self.resizeColumnsToContents()
        header.setStretchLastSection(True)

    def __create_cell(self, text):
        cell = QTableWidgetItem(text)
        cell.setFlags(QtCore.Qt.ItemIsEnabled)
        return cell

    def clear(self):
        for i in range(self._count_row):
            for j in range(self._count_col):
                self.setItem(i, j, self.__create_cell(''))

    def update_table(self):
        self.clear()
        count = 0
        # заполнение


class TableData(QTableWidget):
    def __init__(self):
        super().__init__()
        self._data = []
        self._count_col = 2
        self._count_row = 20
        self._headers = ['Name', 'Path']
        self.setColumnCount(self._count_col)
        self.setRowCount(self._count_row)
        self.setHorizontalHeaderLabels(self._headers)
        self.__resize_columns()
        self.clear()

    def __resize_columns(self):
        header = self.horizontalHeader()
        self.resizeColumnsToContents()
        header.setStretchLastSection(True)

    def __create_cell(self, text):
        cell = QTableWidgetItem(text)
        cell.setFlags(QtCore.Qt.ItemIsEnabled)
        return cell

    def clear_table(self):
        for i in range(self._count_row):
            for j in range(self._count_col):
                self.setItem(i, j, self.__create_cell(''))

    def update(self):
        self.clear()
        count = 0
        for data in self._data:
            self.setItem(count, 0, self.__create_cell(data.name))
            self.setItem(count, 1, self.__create_cell(data.path))
            count += 1


class TableTestConfig(QTableWidget):
    def __init__(self):
        super().__init__()
        self._tests = []
        self._count_col = 12
        self._count_row = 20
        self._headers = ['Model', 'Dataset', 'InferenceFramework', 'BatchSize', 'Device', 'IterationCount',
                         'TestTimeLimit', 'Mode', 'Extension', 'AsyncRequestCount', 'ThreadCount', 'StreamCount']
        self.setColumnCount(self._count_col)
        self.setRowCount(self._count_row)
        self.setHorizontalHeaderLabels(self._headers)
        self.__resize_columns()
        self.clear()

    def __resize_columns(self):
        header = self.horizontalHeader()
        self.resizeColumnsToContents()
        header.setStretchLastSection(True)

    def __create_cell(self, text):
        cell = QTableWidgetItem(text)
        cell.setFlags(QtCore.Qt.ItemIsEnabled)
        return cell

    def clear(self):
        for i in range(self._count_row):
            for j in range(self._count_col):
                self.setItem(i, j, self.__create_cell(''))

    def update(self):
        self.clear()
        count = 0
        # заполнение


class TableRemoteConfig(QTableWidget):
    def __init__(self):
        super().__init__()
        self._parameters = []
        self._count_col = 8
        self._count_row = 100
        self._headers = ['IP', 'Login', 'Password', 'OS', 'FTPClientPath', 'BenchmarkConfig', 'LogFile', 'ResultFile']
        self.setColumnCount(self._count_col)
        self.setRowCount(self._count_row)
        self.setHorizontalHeaderLabels(self._headers)
        self.__resize_columns()
        self.clear()

    def __resize_columns(self):
        header = self.horizontalHeader()
        self.resizeColumnsToContents()
        header.setStretchLastSection(True)

    def __create_cell(self, text):
        cell = QTableWidgetItem(text)
        cell.setFlags(QtCore.Qt.ItemIsEnabled)
        return cell

    def clear(self):
        for i in range(self._count_row):
            for j in range(self._count_col):
                self.setItem(i, j, self.__create_cell(''))

    def update(self):
        self.clear()
        count = 0
        # заполнение


class TableDeployConfig(QTableWidget):
    def __init__(self):
        super().__init__()
        self.__count_col = 5
        self.__count_row = 100
        self.__headers = ['IP', 'Login', 'Password', 'OS', 'DownloadFolder']
        self.__selected_rows = []
        self.setColumnCount(self.__count_col)
        self.setRowCount(self.__count_row)
        self.setHorizontalHeaderLabels(self.__headers)
        self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.__resize_columns()
        self.clear()
        self.clicked.connect(self.clicked_table)

    def __resize_columns(self):
        header = self.horizontalHeader()
        self.resizeColumnsToContents()
        header.setStretchLastSection(True)

    def __create_cell(self, text):
        cell = QTableWidgetItem(text)
        cell.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        return cell

    def clear(self):
        for i in range(self.__count_row):
            for j in range(self.__count_col):
                self.setItem(i, j, self.__create_cell(''))

    def update(self, computers):
        self.clear()
        count = 0
        for i in range(len(computers)):
            self.setItem(i, 0, self.__create_cell(computers[i].get_ip()))
            self.setItem(i, 1, self.__create_cell(computers[i].get_login()))
            self.setItem(i, 2, self.__create_cell(computers[i].get_password()))
            self.setItem(i, 3, self.__create_cell(computers[i].get_os()))
            self.setItem(i, 4, self.__create_cell(computers[i].get_download_folder()))
            count += 1

    def clicked_table(self):
        self.__selected_rows = list(dict.fromkeys([index.row() for index in self.selectedIndexes()]))
        self.__selected_rows.sort()
        self.__selected_rows.reverse()

    def get_selected_rows(self):
        return self.__selected_rows

    def remove_selection(self):
        for index in self.selectedIndexes():
            self.itemFromIndex(index).setSelected(False)