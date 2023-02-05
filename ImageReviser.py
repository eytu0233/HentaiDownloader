import os
import logging
import sys
import math
from PIL import Image

IMAGE_PART_NUM = 6


def revise_image(image_path):
    image = Image.open(image_path)
    width, height = image.size

    revised_img = Image.new('RGB', image.size)
    remainder = int(height % IMAGE_PART_NUM)
    copy_width = width
    for i in range(IMAGE_PART_NUM):
        copy_height = math.floor(height / IMAGE_PART_NUM)
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


def revise_image_dir(target_dir):
    for image_file in os.listdir(target_dir):
        revise_image(f'{target_dir}/{image_file}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s : %(message)s',
                        handlers=[
                            # logging.FileHandler("{0}/{1}.log".format(logPath, fileName)),
                            logging.StreamHandler(sys.stdout)
                        ])