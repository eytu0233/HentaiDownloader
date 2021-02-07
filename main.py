import logging
import os
import sys
from PIL import Image

from PySide2.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QProgressBar, QHeaderView, QLabel, QMenu
from PySide2.QtCore import QThreadPool, Qt, QMutex, QPoint, QThread, QRunnable

from EHentaiDownloader import EHentaiParser
from EighteenComicDownloader import EighteenComicParser
from NHentaiDownloader import NHentaiParser
from WNACGDownloader import WNACGParser
from AHentaiDownloader import AHentaiParser
from ui import Ui_MainWindow

STATUS_PENDING = '列隊中'
STATUS_DOWNLOADING = '下載中'
STATUS_DOWNLOADED = '下載完成'
STATUS_FAIL = '下載失敗'
IMAGE_PART_NUM = 10


class MainWindow(QMainWindow):

    class Checker(QRunnable):
        def __init__(self, url, main_obj):
            super(MainWindow.Checker, self).__init__()
            self.url = url
            self.mainObj = main_obj

        def run(self):
            self.mainObj.start_parser(self.url)

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.tableWidgetDownload.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ui.tableWidgetDownload.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableWidgetDownload.customContextMenuRequested.connect(self.generate_menu)

        self.ui.lineEditFilePath.setText(u"F:\合集\\")
        self.ui.lineEditDownloadUrl.setText('')
        self.ui.btnStartDownload.pressed.connect(self.click_event)

        self.clipBoard = QApplication.clipboard()
        self.clipBoard.dataChanged.connect(self.monitor_clipboard)
        self.mimeData = self.clipBoard.mimeData()
        self.clipBoard.setText("")
        self.parserList = []
        self.downloaderList = []

        self.checkerThreadPool = QThreadPool()
        self.checkerThreadPool.setMaxThreadCount(1)
        self.parserThreadPool = QThreadPool()
        self.ehentaiThreadPool = QThreadPool()
        self.nhentaiThreadPool = QThreadPool()
        self.nhentaiThreadPool.setMaxThreadCount(1)
        self.wnacgThreadPool = QThreadPool()
        self.wnacgThreadPool.setMaxThreadCount(1)
        self.eighteenComicThreadPool = QThreadPool()
        self.ahentaiThreadPool = QThreadPool()

    def generate_menu(self, pos):
        row_num = -1
        for i in self.ui.tableWidgetDownload.selectionModel().selection().indexes():
            row_num = i.row()

        if row_num >= 0:
            menu = QMenu()
            copy_url_action = menu.addAction(u'複製網址')
            redownload_action = menu.addAction(u'重新下載')
            rearrange_action = menu.addAction(u'圖片修正')
            action = menu.exec_(self.ui.tableWidgetDownload.mapToGlobal(pos + QPoint(0, 30)))
            if action == copy_url_action:
                self.clipBoard.setText(self.parserList[row_num].url)
            if action == redownload_action:
                logging.debug(f'item2')
            if action == rearrange_action:
                dir_path = self.parserList[row_num].path
                logging.debug(f'圖片修正 : {dir_path}')

    def monitor_clipboard(self):
        data = self.mimeData.text()
        checker = self.Checker(data, self)
        self.checkerThreadPool.start(checker)

    def click_event(self):
        logging.info('click_event')
        url = self.ui.lineEditDownloadUrl.text()
        self.start_parser(url)

    def start_parser(self, url):
        logging.debug(f'Start start_parser : "{url}"')

        for parser in self.parserList:
            if parser.url == url:
                return

        path = self.ui.lineEditFilePath.text()

        parsers = [
            EHentaiParser(url, path, self.ehentaiThreadPool),
            NHentaiParser(url, path, self.nhentaiThreadPool),
            WNACGParser(url, path, self.wnacgThreadPool),
            EighteenComicParser(url, path, self.eighteenComicThreadPool),
            AHentaiParser(url, path, self.ahentaiThreadPool)
        ]

        for parser in parsers:
            if parser.check():
                self.parserList.append(parser)
                parser.signal.parsed.connect(self.add_download_item)
                self.parserThreadPool.start(parser)
        logging.debug(f'End start_parser : "{url}"')

    def add_download_item(self, downloader):
        for historyDownloader in self.downloaderList:
            if historyDownloader.name == downloader.name and \
                    (historyDownloader.status == STATUS_PENDING or
                     historyDownloader.status == STATUS_DOWNLOADING or
                     historyDownloader.status == STATUS_DOWNLOADED):
                return
        self.downloaderList.append(downloader)
        comic_name = downloader.name
        table = self.ui.tableWidgetDownload
        row_count = table.rowCount()
        table.setRowCount(row_count + 1)

        comic_name_cell = QTableWidgetItem(comic_name)
        comic_name_cell.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        progress_bar_cell = QProgressBar()
        progress_bar_cell.setRange(0, 100)
        progress_bar_cell.setAlignment(Qt.AlignCenter)
        status_cell = QLabel(STATUS_PENDING)
        status_cell.setAlignment(Qt.AlignCenter)
        table.setItem(row_count, 0, comic_name_cell)
        table.setCellWidget(row_count, 1, status_cell)
        table.setCellWidget(row_count, 2, progress_bar_cell)

        downloader.signal.status.connect(status_cell.setText)
        downloader.signal.progress.connect(progress_bar_cell.setValue)
        downloader.start_download()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s : %(message)s',
                        handlers=[
                            # logging.FileHandler("{0}/{1}.log".format(logPath, fileName)),
                            logging.StreamHandler(sys.stdout)
                        ])
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('chardet.charsetprober').setLevel(logging.WARNING)
    logging.getLogger('concurrent').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
