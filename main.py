import logging
import os
import sys
import csv
from datetime import datetime
from PIL import Image

from PySide2.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QProgressBar, QHeaderView, QLabel, QMenu, QFileDialog, QMessageBox, QAction
from PySide2.QtCore import QThreadPool, Qt, QMutex, QPoint, QThread, QRunnable

from EHentaiDownloader import EHentaiParser
from EighteenComicDownloader import EighteenComicParser
from NHentaiDownloader import NHentaiParser
from WNACGDownloader import WNACGParser
from AHentaiDownloader import AHentaiParser
from ImHentaiDownloader import ImHentaiParser
from ui import Ui_MainWindow
from Downloader import (STATUS_PENDING, STATUS_DOWNLOADING, STATUS_DOWNLOADED,
                        STATUS_FAIL, STATUS_UNZIP_FAIL, STATUS_UNZIPING, STATUS_UNZIP)

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

        self.ui.lineEditFilePath.setText(u"E:\\video\合集\\downloads\\")
        self.ui.lineEditDownloadUrl.setText('')
        self.ui.btnStartDownload.pressed.connect(self.click_event)

        # 添加選單列功能
        self.setup_menubar()

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
        self.imhentaiThreadPool = QThreadPool()

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
                logging.debug(f'row_num : {row_num} url : {self.parserList[row_num].url}')
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
            AHentaiParser(url, path, self.ahentaiThreadPool),
            ImHentaiParser(url, path, self.imhentaiThreadPool)
        ]

        for parser in parsers:
            if parser.check():
                self.parserList.append(parser)
                parser.signal.parsed.connect(self.add_download_item)
                self.parserThreadPool.start(parser)
        logging.debug(f'End start_parser : "{url}"')

    def setup_menubar(self):
        """設置選單列"""
        # 創建「工具」選單
        tool_menu = self.ui.menubar.addMenu(u'工具(&T)')

        # 添加「導出失敗項目」動作
        export_action = QAction(u'導出失敗項目(&E)', self)
        export_action.setStatusTip(u'導出下載失敗和解壓縮失敗的項目到CSV文件')
        export_action.triggered.connect(self.export_failed_downloads)
        tool_menu.addAction(export_action)

        # 可以在此添加更多工具選單項目
        tool_menu.addSeparator()

        # 添加「清除失敗項目」動作（未來功能）
        # clear_action = QAction(u'清除失敗項目', self)
        # clear_action.triggered.connect(self.clear_failed_downloads)
        # tool_menu.addAction(clear_action)

    def export_failed_downloads(self):
        """導出失敗的下載項目到CSV文件（包含下載失敗和解壓縮失敗）"""
        failed_items = []

        # 收集失敗的項目（包含下載失敗和解壓縮失敗）
        for i, downloader in enumerate(self.downloaderList):
            if downloader.status == STATUS_FAIL or downloader.status == STATUS_UNZIP_FAIL:
                url = self.parserList[i].url if i < len(self.parserList) else 'N/A'
                failed_items.append({
                    'name': downloader.name,
                    'url': url,
                    'path': downloader.path,
                    'status': downloader.status
                })

        if not failed_items:
            QMessageBox.information(self, u'導出結果', u'沒有失敗的下載項目')
            return

        # 選擇保存位置
        default_filename = f"failed_downloads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            u'保存失敗項目列表',
            default_filename,
            u'CSV文件 (*.csv);;文本文件 (*.txt);;所有文件 (*.*)'
        )

        if not file_path:
            return

        try:
            # 寫入CSV文件
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['檔案名稱', 'URL', '下載路徑', '失敗狀態']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for item in failed_items:
                    writer.writerow({
                        '檔案名稱': item['name'],
                        'URL': item['url'],
                        '下載路徑': item['path'],
                        '失敗狀態': item['status']
                    })

            QMessageBox.information(
                self,
                u'導出成功',
                f'成功導出 {len(failed_items)} 個失敗項目到:\n{file_path}'
            )
            logging.info(f'Exported {len(failed_items)} failed items to {file_path}')

        except Exception as e:
            QMessageBox.critical(self, u'導出失敗', f'導出時發生錯誤:\n{str(e)}')
            logging.error(f'Failed to export: {e}')

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

        # 限制顯示長度為 32 個字元
        display_name = comic_name if len(comic_name) <= 32 else comic_name[:29] + '...'
        comic_name_cell = QTableWidgetItem(display_name)
        comic_name_cell.setToolTip(comic_name)  # 完整名稱顯示在提示中
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
