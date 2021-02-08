import concurrent.futures
import logging
import os
import re
import urllib.request

from bs4 import BeautifulSoup
from Downloader import Downloader, Parser, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_FAIL


class AHentaiParser(Parser):

    def __init__(self, url, path, pool):
        super(AHentaiParser, self).__init__(url, path, pool)

    def check(self):
        match = re.match('^https?://ahentai.top/index.php.+comic_id=(\\d+).*', self.url)
        if match is not None and match.group(1) is not None:
            logging.info(f'parse AHentai')
            self.url = f'https://ahentai.top/index.php?route=comic/readOnline&comic_id={match.group(1)}&host_id=0'
            return True
        return False

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            result = urllib.request.urlopen(req, timeout=20).read()
            soup = BeautifulSoup(result, 'html.parser')

            comic_name = soup.find('span', {"class": "d"}).text
            # 剔除windows不合法路徑字元
            comic_name = re.sub('[\\\\<>:"?*/\t]', '', comic_name)
            comic_name = comic_name.strip()
            logging.debug(f'comic name = \"{comic_name}\"')

            match = re.search('HTTP_IMAGE.+\"(.+)\"', result.decode('utf-8'))
            if match is None or match.group(1) is None:
                raise Exception(f"Can't parse url")
            url = f"http:{match.group(1)}"
            logging.debug(f'url = \"{url}\"')

            match = re.search('Image_List = .+\"(\\d+)\"', result.decode('utf-8'))
            if match is None or match.group(1) is None:
                raise Exception(f"Can't parse page")
            pages = int(match.group(1))
            logging.debug(f'pages = \"{pages}\"')

            match = re.search('Image_List = .+\"extension\":\"(.+)\"', result.decode('utf-8'))
            if match is None or match.group(1) is None:
                raise Exception(f"Can't parse extension")
            extension = match.group(1)
            logging.debug(f'extension = \"{extension}\"')

            self.signal.parsed.emit(AHentaiDownloader(self.path,
                                                      comic_name,
                                                      self.pool,
                                                      url,
                                                      pages,
                                                      extension))
        except Exception as e:
            logging.error(e)


class AHentaiDownloader(Downloader):

    def __init__(self, path, name, pool, url, pages, extension):
        super(AHentaiDownloader, self).__init__(f'{path}{name}', name, pool)
        self.url = url
        self.pages = pages
        self.extension = extension
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
                                    f'{self.url}/{page}.{self.extension}',
                                    f'{self.path}\{page}.{self.extension}'): page for page in range(1, self.pages + 1)}
                for future in concurrent.futures.as_completed(future_to_url):
                    page = future_to_url[future]

                    try:
                        if future.result():
                            self.downloaded += 1
                            self.signal.progress.emit(int(self.downloaded / self.pages * 100))

                    except Exception as e:
                        logging.warning(f"{e} : {self.url}/{page}.{self.extension}")
                        another_ext = 'png' if self.extension == 'jpg' else 'jpg'
                        try:
                            another_future = executor.submit(self.download_url,
                                                             f'{self.url}/{page}.{another_ext}',
                                                             f'{self.path}\{page}.{another_ext}')
                            if another_future.result():
                                self.downloaded += 1
                                self.signal.progress.emit(int(self.downloaded / self.pages * 100))
                        except Exception as e:
                            logging.error(e)
                            logging.error(
                                f"fail download {self.url}/{page}.{another_ext}")
                            pass

        except Exception as e:
            raise e
        finally:
            self.signal.status.emit(STATUS_DOWNLOADED if self.downloaded == self.pages else STATUS_FAIL)
            self.signal.finished.emit()
