import base64
import concurrent.futures
import hashlib
import logging
import math
import os
import re
import urllib.request

from PIL import Image

import ImageReviser

from bs4 import BeautifulSoup
from Downloader import Downloader, Parser, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_FAIL


class EighteenComicParser(Parser):

    def __init__(self, url, path, pool):
        super(EighteenComicParser, self).__init__(url, path, pool)
        self.id = 0

    def check(self):
        match = re.match('^https?://18comic.(org|vip)/(photo|album)/(\\d+)', self.url)
        if match is not None:
            logging.info(f'parse EighteenComic')
            logging.info(f'{match.group(1)} {match.group(2)} {match.group(3)}')
            if match.group(2) == "album":
                self.url = f'https://18comic.org/photo/{match.group(3)}/'
            self.id = match.group(3)
            return True
        return False

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            result = urllib.request.urlopen(req, timeout=20).read()
            soup = BeautifulSoup(result, 'html.parser')
            comic_name = soup.find('title').text

            match = re.match('^([^\\|]+)(\\|.+)? Comics', comic_name)
            if match is None or match.group(1) is None:
                raise Exception(f"Can't parse comic_name \"{comic_name}\"")
            comic_name = match.group(1)

            # 剔除windows不合法路徑字元
            comic_name = re.sub('[\\\\<>:"?*/\t]', '', comic_name)
            comic_name = comic_name.strip()
            logging.debug(f'comic name = \"{comic_name}\"')

            pages = 0
            page_spans = soup.find_all('span', id='nowpage')
            for page_span in page_spans:
                page = int(page_span.text)
                if page > pages:
                    pages = page
            logging.debug(f'pages = \"{pages}\"')

            match = re.search('scramble_id = (\\d+)', result.decode('utf-8'))
            if match is None or match.group(1) is None:
                raise Exception(f"Can't parse scramble_id")
            scramble_id = match.group(1)
            logging.debug(f'scramble_id = \"{scramble_id}\"')

            match = re.search('aid = (\\d+)', result.decode('utf-8'))
            if match is None or match.group(1) is None:
                raise Exception(f"Can't parse aid")
            aid = match.group(1)
            logging.debug(f'aid = \"{aid}\"')

            self.signal.parsed.emit(EighteenComicDownloader(self.path,
                                                            comic_name,
                                                            self.pool,
                                                            self.id,
                                                            pages,
                                                            True))
            self.path = f'{self.path}{comic_name}'
        except Exception as e:
            logging.error(e)


class EighteenComicDownloader(Downloader):

    def __init__(self, path, name, pool, id, pages, is_scramble):
        super(EighteenComicDownloader, self).__init__(f'{path}{name}', name, pool)
        self.id = id
        self.pages = pages
        self.downloaded = 0
        self.is_scramble = is_scramble
        self.file_ext = 'webp'

    def download_url(self, url, path, page):
        urllib.request.urlretrieve(url, path)

        ret = False
        if os.path.getsize(path) < 1:
            ret = self.download_url(url, path)
        else:
            ret = True
            if self.is_scramble:
                self.image_post_process(page)

        return ret

    @staticmethod
    def revise_image(image_path, split_num):
        image = Image.open(image_path)
        width, height = image.size

        revised_img = Image.new('RGB', image.size)
        remainder = int(height % split_num)
        copy_width = width
        for i in range(split_num):
            copy_height = math.floor(height / split_num)
            py = copy_height * i
            y = height - (copy_height * (i + 1)) - remainder
            if i == 0:
                copy_height = copy_height + remainder
            else:
                py = py + remainder

            cropped_img = image.crop((0, y, copy_width, y + copy_height))
            revised_area = (0, py, copy_width, py + copy_height)
            revised_img.paste(cropped_img, revised_area)
        revised_img.save(image_path)

    def image_post_process(self, page):
        combine = f'{self.id}{str(page).zfill(5)}'
        #logging.debug(f'combine=\'{combine}\'')
        md5_hash = hashlib.md5(combine.encode()).hexdigest()
        #logging.debug(f'md5_hash={md5_hash}')
        last_char = md5_hash[-1]
        ascii_value = ord(last_char)
        split_num = 2 + (ascii_value % 8) * 2
        #logging.debug(f'split_num={split_num}')

        self.revise_image(f'{self.path}\{page}.{self.file_ext}', split_num)

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
                                    f'https://cdn-msp.18comic.org/media/photos/{self.id}/{str(page).zfill(5)}.{self.file_ext}',
                                    f'{self.path}\{page}.{self.file_ext}', page): page for page in range(1, self.pages + 1)
                }
                for future in concurrent.futures.as_completed(future_to_url):
                    page = future_to_url[future]

                    try:
                        if future.result():
                            self.downloaded += 1
                            self.signal.progress.emit(int(self.downloaded / self.pages * 100))

                    except Exception as e:
                        logging.error(e)
                        logging.error(f"fail download https://cdn-msp.18comic.org/media/photos/"
                                      f"{self.id}/{str(page).zfill(5)}.{self.file_ext}")
                        pass

        except Exception as e:
            raise e
        finally:
            self.signal.status.emit(STATUS_DOWNLOADED if self.downloaded == self.pages else STATUS_FAIL)
            self.signal.finished.emit()
