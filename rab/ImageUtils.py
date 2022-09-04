import logging
import os
from datetime import datetime as dt
from datetime import timedelta
import sys

import cv2
import imutils
import numpy as np
from pathlib import Path

import pytesseract
if sys.platform == 'win32':
    if Path('Tesseract-OCR/tesseract.exe').is_file():
        pytesseract.pytesseract.tesseract_cmd = r'Tesseract-OCR\tesseract.exe'
        tool = pytesseract
    else:
        #tools = pyocr.get_available_tools()
        tool = pytesseract
        #tool = tools[0]
else:
    #import pyocr
    #tools = pyocr.get_available_tools()
    tool = pytesseract
    #tool = tools[0]

logger = logging.getLogger(__name__)

screenshot_dir = 'screenshots'


def get_center_point(box_coordinates):
    """
    Returns the center point coordinate of a rectangle.
    """
    x1, y1, x2, y2 = box_coordinates
    return [int((x1 + x2) / 2), int((y1 + y2) / 2)]


def save_screenshot(im, main_dir=screenshot_dir, sub_dir=None, save=False, filename=None):
    if save:
        dir_ = main_dir + '/' + sub_dir if sub_dir else main_dir
        if '//' in dir_:
            dir_ = dir_.replace('//','/')
        if not os.path.isdir(dir_):
            os.makedirs(dir_)
        if not filename:
            filename = os.path.join(dir_, (dt.utcnow() + timedelta(hours=8)).strftime('%Y%m%d%H%M%S') + '.png')
        else:
            filename = os.path.join(dir_, filename)
        im.save(filename)
        logger.debug('Saved screenshot to {}.'.format(dir_))
    return


def binarize_image(im, threshold=200, reverse=False):
    # im = Image.open(im_path)
    """Binarize an image."""
    image = im.convert('L')  # convert image to monochrome
    if not reverse:
        bin_im = image.point(lambda p: p > threshold and 255)
    else:
        bin_im = image.point(lambda p: p <= threshold and 255)
    return bin_im


def extract_text_from_image(im, binary=True, threshold=200, reverse=False):
    if binary:
        im_transformed = binarize_image(im, threshold, reverse)
    else:
        im_transformed = im.convert('L')
    # save_screenshot(im_binary, sub_dir='binary', save=True)
    return tool.image_to_string(im_transformed).replace("\n", " ").lower().strip()


def crop_middle(im):
    w, h = im.size
    w0, h0 = w // 3, h // 3
    return im.crop((0, h0, w, h0 * 2))


def crop_top_half(im):
    w, h = im.size
    w0, h0 = w // 2, h // 2
    return im.crop((0, 0, w, h0))


def crop_bottom_half(im):
    w, h = im.size
    w0, h0 = w // 2, h // 2
    return im.crop((0, h0, w, h))


def crop_horizontal_piece(im, n=2, i=1):
    # split the image into n pieces, and take the ith
    w, h = im.size
    h0 = h // n
    return im.crop((0, h0 * (i - 1), w, h0 * i))

def crop_top_by_percent(im, percent=70):
    # crop top image by percentage
    w, h = im.size
    new_height = percent/100*h
    return im.crop((0,0,w,new_height))

def create_range_color_set(r, g, b, difference=20):
    final_set = []
    x = range(-difference, difference + 1)
    for n in x:
        rset = r + n
        if reset < 0:
            reset = 255 + reset
        if reset > 255:
            reset = reset - 255
        newset = (rset, g, b)
        final_set.append(newset)
        rset = g + n
        if reset < 0:
            reset = 255 + reset
        if reset > 255:
            reset = reset - 255
        newset = (r, rset, b)
        final_set.append(newset)
        rset = b + n
        if reset < 0:
            reset = 255 + reset
        if reset > 255:
            reset = reset - 255
        newset = (r, g, rset)
        final_set.append(newset)
    return final_set

def compare_image(img1, img2):
    if img1.size != img2.size or img1.getbands() != img2.getbands():
            return -1
    s = 0
    for band_index, band in enumerate(img1.getbands()):
        m1 = np.array([p[band_index] for p in img1.getdata()]).reshape(*img1.size)
        m2 = np.array([p[band_index] for p in img2.getdata()]).reshape(*img2.size)
        s += np.sum(np.abs(m1-m2))
    return s

def match_template(template_path, im, threshold=20000000, resize_template=False):
    # load the image image, convert it to grayscale, and detect edges
    template = cv2.imread(template_path)
    if resize_template:
        template = imutils.resize(template, width=50)
    template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    template = cv2.Canny(template, 50, 200)
    (tH, tW) = template.shape[:2]
    # plt.imshow(template)
    # plt.show()

    # image = im.convert('RGB')
    gray = np.array(im)
    gray = gray[:, :, ::-1].copy()
    im_rgb = cv2.cvtColor(gray, cv2.COLOR_BGR2RGB)
    found = None
    # loop over the scales of the image
    for scale in np.linspace(0.2, 1.0, 20)[::-1]:
        # resize the image according to the scale, and keep track
        # of the ratio of the resizing
        resized = imutils.resize(gray, width=int(gray.shape[1] * scale))
        r = gray.shape[1] / float(resized.shape[1])
        # if the resized image is smaller than the template, then break
        # from the loop
        if resized.shape[0] < tH or resized.shape[1] < tW:
            break

        # detect edges in the resized, grayscale image and apply template
        # matching to find the template in the image
        edged = cv2.Canny(resized, 50, 200)
        result = cv2.matchTemplate(edged, template, cv2.TM_CCOEFF)
        (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)

        visualize = False
        # check to see if the iteration should be visualized
        if visualize:
            # draw a bounding box around the detected region
            clone = np.dstack([edged, edged, edged])
            cv2.rectangle(clone, (maxLoc[0], maxLoc[1]),
                          (maxLoc[0] + tW, maxLoc[1] + tH), (0, 0, 255), 2)
            # plt.imshow(clone)
            # plt.show()
            # cv2.imshow("Visualize", clone)
            # cv2.waitKey(0)
        # if we have found a new maximum correlation value, then update
        # the bookkeeping variable
        if found is None or maxVal > found[0]:
            found = (maxVal, maxLoc, r)
    # unpack the bookkeeping variable and compute the (x, y) coordinates
    # of the bounding box based on the resized ratio
    (maxVal, maxLoc, r) = found
    # (startX, startY) = (int(maxLoc[0] * r), int(maxLoc[1] * r))
    # (endX, endY) = (int((maxLoc[0] + tW) * r), int((maxLoc[1] + tH) * r))
    # # draw a bounding box around the detected result and display the image
    # cv2.rectangle(im_rgb, (startX, startY), (endX, endY), (255, 0, 0), 2)
    # plt.figure(figsize=(20, 10))
    # plt.imshow(im_rgb)
    # plt.show()
    return found, True if maxVal >= threshold else False