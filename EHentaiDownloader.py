import concurrent.futures
import logging
import os
import re
import urllib.request

from bs4 import BeautifulSoup
from Downloader import Downloader, Parser, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_FAIL


class EHentaiParser(Parser):

    def __init__(self, url, path, pool):
        super(EHentaiParser, self).__init__(url, path, pool)

    def check(self):
        match = re.match('^https://e-hentai.org/g/', self.url)
        if match is not None:
            logging.info(f'parse_ehentai')
            return True
        return False

    def parse_ehentai_one_picture(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            result = urllib.request.urlopen(req, timeout=5).read()
            soup = BeautifulSoup(result, 'html.parser')
            main_div = soup.find('div', id='i3')
            if main_div is None:
                raise Exception("Can't parse main_div!")
            #logging.debug(f'main_div = \"{main_div}\"')

            img = main_div.find('img')['src']
            #logging.debug(f'img = \"{img}\"')

            return img
        except Exception as e:
            logging.error(e)
            return None

    def parse_ehentai_picture_pages(self, url, soup=None):
        if soup is None:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            result = urllib.request.urlopen(req, timeout=5).read()
            soup = BeautifulSoup(result, 'html.parser')

        picture_pages = []
        divs = soup.find_all('div', class_='gdtm')
        for div in divs:
            picture_page = div.find('a')['href']
            picture_pages.append(picture_page)
            #logging.debug(picture_page)

        return picture_pages

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            result = urllib.request.urlopen(req, timeout=5).read()
            #logging.debug(result)
            soup = BeautifulSoup(result, 'html.parser')
            comic_name = soup.find('h1', id='gj').text
            if len(comic_name) == 0:
                raise Exception("Can't parse comic_name!")
            # 剔除windows不合法路徑字元
            comic_name = re.sub('[\\\\<>:"?*/\t]', '', comic_name)
            logging.debug(f'comic name = \"{comic_name}\"')

            tds = soup.find_all('td', class_='gdt2')
            pages = 0
            matcher = re.compile('(\\d+) pages')
            for td in tds:
                match = matcher.match(td.text)
                if match is not None and match.group(1) is not None:
                    pages = int(match.group(1))
                    logging.debug(f'pages = {pages}')
                    break

            imgs = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
                all_target = self.parse_ehentai_picture_pages(None, soup=soup)
                for page in range(1, int(pages / 40) + 1):
                    all_target = all_target + self.parse_ehentai_picture_pages(f'{self.url}?p={page}')
                future_to_url = {executor.submit(self.parse_ehentai_one_picture, url): url for url in all_target}
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        img = future.result()
                    except Exception as exc:
                        logging.error(f'{url} genrated an exception : {exc}')
                    else:
                        #logging.debug(f'img = {img}')
                        imgs.append(img)

            self.signal.parsed.emit(EHentaiDownloader(self.path, comic_name, self.pool, imgs))
        except Exception as e:
            logging.error(e)


class EHentaiDownloader(Downloader):

    def __init__(self, path, name, pool, images):
        super(EHentaiDownloader, self).__init__(f'{path}{name}', name, pool)
        self.images = images

    def run(self):
        logging.debug(f'download {self.path}')
        self.signal.status.emit(STATUS_DOWNLOADING)
        total = len(self.images)
        downloaded = 0

        if not os.path.exists(self.path):
            os.mkdir(self.path)

        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            future_to_url = {executor.submit(urllib.request.urlretrieve, url, f'{self.path}\\{url.rsplit("/", 1)[-1]}'):
                                 url for url in self.images}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    future.result()
                except Exception as exc:
                    logging.error(f'{url} genrated an exception : {exc}')
                else:
                    downloaded += 1
                    percent = int(downloaded / total * 100)
                    self.signal.progress.emit(100 if percent > 100 else percent)

        self.signal.status.emit(STATUS_DOWNLOADED if downloaded == total else STATUS_FAIL)
        self.signal.finished.emit()
