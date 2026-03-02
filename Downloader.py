import abc
import re
import logging

from PySide2.QtCore import QObject, Signal, QRunnable

STATUS_PENDING = '列隊中'
STATUS_DOWNLOADING = '下載中'
STATUS_DOWNLOADED = '下載完成'
STATUS_UNZIPING = '解壓縮中'
STATUS_UNZIP = '解壓縮完成'
STATUS_UNZIP_FAIL = '解壓縮失敗'
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
        self.name = self.format_name(name)  # 自動格式化名稱
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

    def check_directory_exists(self, dir_path):
        """
        檢查目錄是否存在且非空
        返回 True 表示目錄已存在且有內容（不需要下載）
        返回 False 表示目錄不存在或為空（需要下載）
        """
        import os
        if not os.path.exists(dir_path):
            return False

        if not os.path.isdir(dir_path):
            return False

        # 檢查目錄是否為空
        if not os.listdir(dir_path):
            return False

        return True

    @staticmethod
    def keep_last_bracket_group(text):
        """
        保留最後一組方括號及其後面的內容
        已棄用，請使用 format_name
        """
        matches = re.findall(r'\[.*?\]', text)

        if matches:
            last_match = matches[-1]
            last_index = text.rfind(last_match)
            return text[last_index:]
        else:
            return text

    @staticmethod
    def format_name(text):
        """
        格式化名稱，只保留 "[作者名]作品名" 格式
        過濾掉 [作者名] 前面的所有字元

        範例:
        "【繁體】[作者名]作品名" -> "[作者名]作品名"
        "(C99) [作者名]作品名" -> "[作者名]作品名"
        "多餘字元[作者1][作者2]作品名" -> "[作者1][作者2]作品名"
        """
        # 找到第一個 [ 的位置
        first_bracket = text.find('[')

        if first_bracket != -1:
            # 保留從第一個 [ 開始的所有內容
            return text[first_bracket:].strip()
        else:
            # 如果沒有方括號，返回原始字串
            return text.strip()

