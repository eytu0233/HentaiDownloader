# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainWindow.ui',
# licensing of 'mainWindow.ui' applies.
#
# Created: Wed May  1 22:07:43 2019
#      by: pyside2-uic  running on PySide2 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tabDownload = QtWidgets.QWidget()
        self.tabDownload.setObjectName("tabDownload")
        self.gridLayout = QtWidgets.QGridLayout(self.tabDownload)
        self.gridLayout.setObjectName("gridLayout")
        self.btnFileExplorer = QtWidgets.QToolButton(self.tabDownload)
        self.btnFileExplorer.setObjectName("btnFileExplorer")
        self.gridLayout.addWidget(self.btnFileExplorer, 0, 3, 1, 1)
        self.lineEditDownloadUrl = QtWidgets.QLineEdit(self.tabDownload)
        self.lineEditDownloadUrl.setObjectName("lineEditDownloadUrl")
        self.gridLayout.addWidget(self.lineEditDownloadUrl, 1, 2, 1, 1)
        self.label = QtWidgets.QLabel(self.tabDownload)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.lineEditFilePath = QtWidgets.QLineEdit(self.tabDownload)
        self.lineEditFilePath.setObjectName("lineEditFilePath")
        self.gridLayout.addWidget(self.lineEditFilePath, 0, 2, 1, 1)
        self.tableWidgetDownload = QtWidgets.QTableWidget(self.tabDownload)
        self.tableWidgetDownload.setEnabled(True)
        self.tableWidgetDownload.setObjectName("tableWidgetDownload")
        self.tableWidgetDownload.setColumnCount(3)
        self.tableWidgetDownload.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidgetDownload.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidgetDownload.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidgetDownload.setHorizontalHeaderItem(2, item)
        self.tableWidgetDownload.horizontalHeader().setStretchLastSection(True)
        self.tableWidgetDownload.verticalHeader().setVisible(False)
        self.gridLayout.addWidget(self.tableWidgetDownload, 2, 0, 1, 4)
        self.btnStartDownload = QtWidgets.QPushButton(self.tabDownload)
        self.btnStartDownload.setObjectName("btnStartDownload")
        self.gridLayout.addWidget(self.btnStartDownload, 1, 3, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.tabDownload)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.tabWidget.addTab(self.tabDownload, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.tabWidget.addTab(self.tab_2, "")
        self.verticalLayout.addWidget(self.tabWidget)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        MainWindow.setTabOrder(self.btnStartDownload, self.tableWidgetDownload)
        MainWindow.setTabOrder(self.tableWidgetDownload, self.lineEditDownloadUrl)
        MainWindow.setTabOrder(self.lineEditDownloadUrl, self.lineEditFilePath)
        MainWindow.setTabOrder(self.lineEditFilePath, self.btnFileExplorer)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtWidgets.QApplication.translate("MainWindow", "nHentai下載器", None, -1))
        self.btnFileExplorer.setText(QtWidgets.QApplication.translate("MainWindow", "...", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("MainWindow", "下載檔案到 : ", None, -1))
        self.tableWidgetDownload.horizontalHeaderItem(0).setText(QtWidgets.QApplication.translate("MainWindow", "檔案名稱", None, -1))
        self.tableWidgetDownload.horizontalHeaderItem(1).setText(QtWidgets.QApplication.translate("MainWindow", "檔案狀態", None, -1))
        self.tableWidgetDownload.horizontalHeaderItem(2).setText(QtWidgets.QApplication.translate("MainWindow", "下載進度", None, -1))
        self.btnStartDownload.setText(QtWidgets.QApplication.translate("MainWindow", "開始下載", None, -1))
        self.label_2.setText(QtWidgets.QApplication.translate("MainWindow", "輸入網址 :", None, -1))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabDownload), QtWidgets.QApplication.translate("MainWindow", "下載", None, -1))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QtWidgets.QApplication.translate("MainWindow", "設定", None, -1))

