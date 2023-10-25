import concurrent.futures
import logging
import os
import re
import urllib.request
import browser_cookie3

from bs4 import BeautifulSoup
from Downloader import Downloader, Parser, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_FAIL


class NHentaiParser(Parser):

    def __init__(self, url, path, pool):
        super(NHentaiParser, self).__init__(url, path, pool)

    def check(self):
        match = re.match('^https://nhentai.net/', self.url)
        if match is not None:
            logging.info(f'parse_nhentai')
            return True
        return False

    def run(self):
        try:
            cj = browser_cookie3.chrome(domain_name='nhentai.net')
            logging.debug(cj)
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36')]
            urllib.request.install_opener(opener)
            req = urllib.request.Request(self.url)
            result = urllib.request.urlopen(req, timeout=5).read()
            soup = BeautifulSoup(result, 'html.parser')
            h2 = soup.find('h2', class_='title')
            if h2 is None:
                comic_name = soup.find('h1', class_='title').text
            else:
                comic_name = h2.text
            if len(comic_name) == 0:
                raise Exception("Can't parse comic_name!")
            # 剔除windows不合法路徑字元
            comic_name = re.sub('[\\\\<>:"?*/\t]', '', comic_name)
            comic_name = comic_name.strip()
            logging.debug(f'comic name = \"{comic_name}\"')

            a = soup.find('img', 'lazyload')
            data_src = a['data-src']
            logging.debug(f'data_src = \"{data_src}\"')
            match = re.match('https://t.*.nhentai.net/galleries/(\\d+)/cover.*', data_src)
            if match is None or match.group(1) is None:
                raise Exception("Can't parse media_id!")

            media_id = match.group(1)
            logging.debug(f'media_id = {media_id}')

            div = soup.find_all('div', class_='tag-container field-name')
            pages = 0
            matcher = re.compile('Pages:(\\d+)')
            for sub_div in div:
                pre_str = "".join(sub_div.text.split())
                logging.debug(f'pre_str = {pre_str}')
                match = matcher.match(pre_str)
                if match is not None and match.group(1) is not None:
                    pages = int(match.group(1))
                    logging.debug(f'pages = {pages}')
                    break

            if pages == 0:
                raise Exception("Can't parse pages")

            """
            artists = soup.select('a[href*="/artist/"]')
            artists_num = len(artists)
            logging.debug(artists)

            language_tag = soup.select('a[href*="/language/"]')
            logging.debug(language_tag)
            for tag in language_tag:
                match = re.match('/language/(\\w+)/', tag['href'])
                if match is not None and match.group(1) != 'translated':
                    language = match.group(1)
                    break
            """

            req = urllib.request.Request(f'{self.url}1/')
            result = urllib.request.urlopen(req, timeout=5).read()
            soup = BeautifulSoup(result, 'html.parser')

            section = soup.find('section', id='image-container')
            img = section.find('img')
            logging.debug(f'img = {img}')
            match = re.match('https://i.*.nhentai.net/galleries/(\\d+)/(\\d+).([a-zA-Z]+)', img['src'])
            if match is None or match.group(3) is None:
                raise Exception("Can't parse ext!")
            ext = match.group(3)

            self.signal.parsed.emit(NHentaiDownloader(self.path, comic_name, self.pool, media_id, pages, ext))
        except Exception as e:
            logging.error(e)


class NHentaiDownloader(Downloader):

    def __init__(self, path, name, pool, id, pages, ext):
        super(NHentaiDownloader, self).__init__(f'{path}{name}', name, pool)
        self.id = id
        self.pages = pages
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
                    executor.submit(self.download_url, f'https://i.nhentai.net/galleries/{self.id}/{page}.{self.ext}',
                                    f'{self.path}\{page}.{self.ext}'): page for page in range(1, self.pages + 1)}
                for future in concurrent.futures.as_completed(future_to_url):
                    page = future_to_url[future]

                    try:
                        if future.result():
                            self.downloaded += 1
                            self.signal.progress.emit(int(self.downloaded / self.pages * 100))
                            # logging.info(f'Finished {self.downloaded}/{self.pages} : {progress}%')

                    except Exception as e:
                        logging.warning(f"{e} : https://i.nhentai.net/galleries/{self.id}/{page}.{self.ext}")
                        another_ext = 'png' if self.ext == 'jpg' else 'jpg'
                        try:
                            another_future = executor.submit(self.download_url,
                                                             f'https://i.nhentai.net/galleries/{self.id}/{page}.{another_ext}',
                                                             f'{self.path}\{page}.{another_ext}')
                            if another_future.result():
                                self.downloaded += 1
                                self.signal.progress.emit(int(self.downloaded / self.pages * 100))
                        except Exception as e:
                            logging.error(e)
                            logging.error(
                                f"fail download https://i.nhentai.net/galleries/{self.id}/{page}.{another_ext}")
                            pass

        except Exception as e:
            raise e
        finally:
            self.signal.status.emit(STATUS_DOWNLOADED if self.downloaded == self.pages else STATUS_FAIL)
            self.signal.finished.emit()
