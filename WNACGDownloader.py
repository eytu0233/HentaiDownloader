import logging
import re
import urllib.request

from bs4 import BeautifulSoup
from Downloader import Downloader, Parser, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_FAIL


class WNACGParser(Parser):

    def __init__(self, url, path, pool):
        super(WNACGParser, self).__init__(url, path, pool)

    def check(self):
        match = re.match('^https?://www.wnacg.(org|com)/photos-index-(page-\\d+)?', self.url)
        if match is not None:
            logging.info(f'parse_wnacg')
            return True
        return False

    def run(self):
        match = re.match('https?://www.wnacg.(org|com)/photos-index(-page-\\d+)?-aid-(\\d+).html', self.url)
        if match is None:
            print(f"\"{url}\" is not match!!")
            return None

        index = match.group(3)

        req = urllib.request.Request(f"http://www.wnacg.org/download-index-aid-{index}.html", headers={'User-Agent': 'Mozilla/5.0'})
        result = urllib.request.urlopen(req, timeout=5).read()
        if result is None:
            logging.error(f"Can't get web page from \"{downloadPageUrl}\"")
            return

        soup = BeautifulSoup(result, 'html.parser')
        comic_name = soup.find('p', 'download_filename').text
        comic_name = re.sub('[\\\\<>:"?*/\t]', '', comic_name)  # 刪除非法文件名
        download_url = soup.find('a', 'down_btn')['href']

        self.signal.parsed.emit(WNACGDownloader(self.path, comic_name, self.pool, download_url))


class WNACGDownloader(Downloader):

    def __init__(self, path, name, pool, url):
        super(WNACGDownloader, self).__init__(f'{path}{name}', name, pool)
        self.url = url

    def callback(self, index, chunk, length):
        percent = int(index * chunk / length * 100)
        self.signal.progress.emit(100 if percent > 100 else percent)

    def run(self):
        self.signal.status.emit(STATUS_DOWNLOADING)
        urllib.request.urlretrieve(self.url, self.path, self.callback)
        self.signal.status.emit(STATUS_DOWNLOADED)
        self.signal.finished.emit()
