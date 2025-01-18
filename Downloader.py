import abc
import re
import logging

from PySide2.QtCore import QObject, Signal, QRunnable

STATUS_PENDING = '列隊中'
STATUS_DOWNLOADING = '下載中'
STATUS_DOWNLOADED = '下載完成'
STATUS_UNZIPING = '解壓縮中'
STATUS_UNZIP = '解壓縮完成'
STATUS_UNZIP_FAIL = '解壓縮完成'
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
    def keep_last_bracket_group(text):
        # 使用正則表達式找到所有方括號組
        matches = re.findall(r'\[.*?\]', text)

        if matches:
            # 找到最後一組方括號
            last_match = matches[-1]
            # 在原始字串中查找該最後匹配的方括號並保留它後面的所有內容
            last_index = text.rfind(last_match)
            return text[last_index:]
        else:
            # 如果找不到方括號組，返回原始字串
            return text

