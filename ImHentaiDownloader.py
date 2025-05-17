import concurrent.futures
import logging
import os
import re
import urllib.request
import browser_cookie3

from bs4 import BeautifulSoup
from Downloader import Downloader, Parser, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_FAIL


class ImHentaiParser(Parser):

    def __init__(self, url, path, pool):
        super(ImHentaiParser, self).__init__(url, path, pool)

    def check(self):
        match = re.match('^https://imhentai.xxx/', self.url)
        if match is not None:
            logging.info(f'parse_imhentai.xxx')
            return True
        return False

    def run(self):
        try:
            #cj = browser_cookie3.chrome(domain_name='parse_imhentai.xxx')
            #logging.debug(cj)
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36')]
            urllib.request.install_opener(opener)
            req = urllib.request.Request(self.url)
            result = urllib.request.urlopen(req, timeout=5).read()
            soup = BeautifulSoup(result, 'html.parser')
            comic_name = soup.find('p', class_='subtitle').text
            if comic_name is None or len(comic_name) == 0:
                raise Exception("Can't parse comic_name!")
            # 剔除windows不合法路徑字元
            comic_name = re.sub('[\\\\<>:"?*/\t|]', '', comic_name)
            comic_name = comic_name.strip()
            logging.debug(f'comic name = \"{comic_name}\"')

            match = re.match('.*/gallery/(\\d+)/.*', self.url)
            if match is None or match.group(1) is None:
                raise Exception("Can't parse media_id!")

            view_id = match.group(1)
            logging.debug(f'view_id = {view_id}')

            li_text = soup.find('li', class_='pages').text
            if li_text is None:
                raise Exception("Can't parse pages!")
            match = re.match('Pages: (\\d+)', li_text)
            if match is None or match.group(1) is None:
                raise Exception("Can't parse media_id!")

            pages = match.group(1)
            logging.debug(f'pages = {pages}')

            req = urllib.request.Request(f'https://imhentai.xxx/view/{view_id}/1/')
            result = urllib.request.urlopen(req, timeout=5).read()
            logging.debug(result)
            soup = BeautifulSoup(result, 'html.parser')

            img = soup.find('img', id='gimg')
            logging.debug(f'img = {img["data-src"]}')
            match = re.match('https://m7.imhentai.xxx/\\d+/(.+)/\\d+.(.+)', img['data-src'])
            if match is None or match.group(1) is None or match.group(2) is None:
                raise Exception("Can't parse ext!")
            media_id = match.group(1)
            logging.debug(f'media_id = {media_id}')
            ext = match.group(2)
            logging.debug(f'ext = {ext}')

            self.signal.parsed.emit(ImHentaiDownloader(self.path, comic_name, self.pool, media_id, pages, ext))
        except Exception as e:
            logging.error(e)


class ImHentaiDownloader(Downloader):

    def __init__(self, path, name, pool, id, pages, ext):
        super(ImHentaiDownloader, self).__init__(f'{path}{name}', name, pool)
        self.id = id
        self.pages = int(pages)
        self.ext = ext
        self.downloaded = 0

    def download_url(self, url, path):
        urllib.request.urlretrieve(url, path)

        return self.download_url(url, path) if os.path.getsize(path) < 1 else True

    def run(self):
        logging.info(f'Downloading : \"{self.path}\"')

        try:
            if not os.path.exists(self.path):
                os.makedirs(self.path)

            self.signal.status.emit(STATUS_DOWNLOADING)

            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
                future_to_url = {
                    executor.submit(self.download_url, f'https://m7.imhentai.xxx/022/{self.id}/{page}.{self.ext}',
                                    f'{self.path}\{page}.{self.ext}'): page for page in range(1, self.pages + 1)}
                for future in concurrent.futures.as_completed(future_to_url):
                    page = future_to_url[future]

                    try:
                        if future.result():
                            self.downloaded += 1
                            self.signal.progress.emit(int(self.downloaded / self.pages * 100))
                            # logging.info(f'Finished {self.downloaded}/{self.pages} : {progress}%')

                    except Exception as e:
                        logging.warning(f"{e} : https://m7.imhentai.xxx/022/{self.id}/{page}.{self.ext}")
                        another_ext = 'png' if self.ext == 'jpg' else 'jpg'
                        try:
                            another_future = executor.submit(self.download_url,
                                                             f'https://m7.imhentai.xxx/022/{self.id}/{page}.{another_ext}',
                                                             f'{self.path}\{page}.{another_ext}')
                            if another_future.result():
                                self.downloaded += 1
                                self.signal.progress.emit(int(self.downloaded / self.pages * 100))
                        except Exception as e:
                            logging.error(e)
                            logging.error(
                                f"fail download https://m7.imhentai.xxx/022/{self.id}/{page}.{another_ext}")
                            pass

        except Exception as e:
            raise e
        finally:
            self.signal.status.emit(STATUS_DOWNLOADED if self.downloaded == self.pages else STATUS_FAIL)
            self.signal.finished.emit()
