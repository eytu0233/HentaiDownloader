import logging
import sys

from PySide2.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QProgressBar, QHeaderView, QLabel
from PySide2.QtCore import QThreadPool, Qt

from EHentaiDownloader import EHentaiParser
from EighteenComicDownloader import EighteenComicParser
from NHentaiDownloader import NHentaiParser
from WNACGDownloader import WNACGParser
from ui import Ui_MainWindow

STATUS_PENDING = '列隊中'
STATUS_DOWNLOADING = '下載中'
STATUS_DOWNLOADED = '下載完成'
STATUS_FAIL = '下載失敗'

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.tableWidgetDownload.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        self.ui.lineEditFilePath.setText(u"F:\合集\\")
        self.ui.lineEditDownloadUrl.setText('')
        self.ui.btnStartDownload.pressed.connect(self.click_event)

        self.clipBoard = QApplication.clipboard()
        self.clipBoard.dataChanged.connect(self.monitor_clipboard)
        self.mimeData = self.clipBoard.mimeData()
        self.clipBoard.setText("")
        self.oldData = ""

        self.parserThreadPool = QThreadPool()
        self.ehentaiThreadPool = QThreadPool()
        self.nhentaiThreadPool = QThreadPool()
        self.nhentaiThreadPool.setMaxThreadCount(1)
        self.wnacgThreadPool = QThreadPool()
        self.wnacgThreadPool.setMaxThreadCount(1)
        self.eighteenComicThreadPool = QThreadPool()

    def monitor_clipboard(self):
        data = self.mimeData.text()
        if data == self.oldData:
            return
        self.oldData = data
        self.start_parser(data)

    def click_event(self):
        logging.info('click_event')
        url = self.ui.lineEditDownloadUrl.text()
        self.start_parser(url)

    def start_parser(self, url):
        logging.info(f'start_parser {url}')

        path = self.ui.lineEditFilePath.text()

        parsers = [
            EHentaiParser(url, path, self.ehentaiThreadPool),
            NHentaiParser(url, path, self.nhentaiThreadPool),
            WNACGParser(url, path, self.wnacgThreadPool),
            EighteenComicParser(url, path, self.eighteenComicThreadPool)
        ]

        for parser in parsers:
            if parser.check():
                parser.signal.parsed.connect(self.add_download_item)
                self.parserThreadPool.start(parser)

    def add_download_item(self, downloader):

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
