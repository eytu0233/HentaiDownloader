import abc

from PySide2.QtCore import QObject, Signal, QRunnable

STATUS_PENDING = '列隊中'
STATUS_DOWNLOADING = '下載中'
STATUS_DOWNLOADED = '下載完成'
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
        self.signal = self.DownloadSignal()

    def name(self):
        return self.name

    def start_download(self):
        self.pool.start(self)


