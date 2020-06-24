import concurrent.futures
import logging
import os
import re
import urllib.request

from bs4 import BeautifulSoup
from Downloader import Downloader, Parser, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_FAIL


class EighteenComicParser(Parser):

    def __init__(self, url, path, pool):
        super(EighteenComicParser, self).__init__(url, path, pool)
        self.id = 0

    def check(self):
        match = re.match('^https?://18comic.org/(photo|album)/(\\d+)', self.url)
        if match is not None:
            logging.info(f'parse EighteenComic')
            if match.group(1) == "album":
                self.url = f'https://18comic.org/photo/{match.group(2)}/'
            self.id = match.group(2)
            return True
        return False

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            result = urllib.request.urlopen(req, timeout=5).read()
            soup = BeautifulSoup(result, 'html.parser')
            comic_name = soup.find('title').text

            match = re.match('^([^\\|]+)(\\|.+)? Comics', comic_name)
            if match is None or match.group(1) is None:
                raise Exception(f"Can't parse comic_name \"{comic_name}\"")
            comic_name = match.group(1)

            # 剔除windows不合法路徑字元
            comic_name = re.sub('[\\\\<>:"?*/\t]', '', comic_name)
            logging.debug(f'comic name = \"{comic_name}\"')

            pages = int(soup.find('span', id='maxpage').text.strip())

            self.signal.parsed.emit(EighteenComicDownloader(self.path, comic_name, self.pool, self.id, pages))
        except Exception as e:
            logging.error(e)


class EighteenComicDownloader(Downloader):

    def __init__(self, path, name, pool, id, pages):
        super(EighteenComicDownloader, self).__init__(f'{path}{name}', name, pool)
        self.id = id
        self.pages = pages
        self.downloaded = 0

    def download_url(self, url, path):
        urllib.request.urlretrieve(url, path)

        return self.download_url(url, path) if os.path.getsize(path) < 1 else True

    def run(self):
        logging.info(f'Downloading : \"{self.path}\"')

        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent',
                              'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1941.0 Safari/537.36')]
        urllib.request.install_opener(opener)

        try:
            if not os.path.exists(self.path):
                os.makedirs(self.path)

            self.signal.status.emit(STATUS_DOWNLOADING)

            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
                future_to_url = {
                    executor.submit(self.download_url,
                                    f'https://cdn-msp.18comic.org/media/photos/{self.id}/{str(page).zfill(5)}.jpg',
                                    f'{self.path}\{page}.jpg'): page for page in range(1, self.pages + 1)}
                for future in concurrent.futures.as_completed(future_to_url):
                    page = future_to_url[future]

                    try:
                        if future.result():
                            self.downloaded += 1
                            self.signal.progress.emit(int(self.downloaded / self.pages * 100))

                    except Exception as e:
                        logging.error(e)
                        logging.error(f"fail download https://cdn-msp.18comic.org/media/photos/{self.id}/{str(page).zfill(5)}.jpg")
                        pass

        except Exception as e:
            raise e
        finally:
            self.signal.status.emit(STATUS_DOWNLOADED if self.downloaded == self.pages else STATUS_FAIL)
            self.signal.finished.emit()
