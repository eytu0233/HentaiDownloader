import abc
import re
import logging

from PySide2.QtCore import QObject, Signal, QRunnable

STATUS_PENDING = '列隊中'
STATUS_DOWNLOADING = '下載中'
STATUS_DOWNLOADED = '下載完成'
STATUS_UNZIPING = '解壓縮中'
STATUS_UNZIP = '解壓縮完成'
STATUS_FAIL = '下載失敗'


class Parser(QRunnable):
    class ParserSignal(QObject):
        parsed = Signal(object)

    def __init__(self, url, path, pool):
        super(Parser, self).__init__()
        self.url = url
        self.path = path
        self.pool = pool
        self.signal = self.ParserSignal()

    @abc.abstractmethod
    def check(self):
        return NotImplemented


class Downloader(QRunnable):
    class DownloadSignal(QObject):
        finished = Signal()
        progress = Signal(int)
        status = Signal(str)

    def __init__(self, path, name, pool):
        super(Downloader, self).__init__()
        self.path = path
        self.name = name
        self.pool = pool
        self.status = STATUS_PENDING
        self.signal = self.DownloadSignal()
        self.signal.status.connect(self.statusSlot)

    def name(self):
        return self.name

    def status(self):
        return self.status

    def statusSlot(self, status):
        self.status = status

    def start_download(self):
        self.pool.start(self)

    @staticmethod
    def remove_content_between_backslash_and_bracket(s):
        # 使用正则表达式替换 \ 和 [ 之间的所有内容，只留下 \ 和 [
        return re.sub(r'(\\)[^\\\[]*?(\[)', r'\1\2', s)
