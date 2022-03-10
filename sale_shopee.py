#!/usr/local/bin/python
# coding: utf-8
'''Tự động đăng nhập facebook
'''
import os
import pickle
import logging
import re
import json

from datetime import datetime
from time import sleep
from typing import Union, AnyStr
from getpass import getpass
from configparser import ConfigParser
import sentry_sdk
from webdriver_manager.firefox import GeckoDriverManager
import requests

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains


EXTRA = dict(cookies_name=None)
TESTING = None
URL = 'https://shopee.vn/flash_sale'
NAME = 'sale_shopee'


def thiet_lap_logging(name):
    sentry_sdk.init(
        'https://2e084979867c4e8c83f0b3b8062afc5b@o1086935.'
        'ingest.sentry.io/6111285',
        traces_sample_rate=1.0,
    )

    log_format = ' - '.join([
        '%(asctime)s',
        '%(name)s',
        '%(levelname)s',
        '%(message)s',
    ])
    formatter = logging.Formatter(log_format)
    file_handles = logging.FileHandler(
        filename='logs.txt',
        mode='a',
        encoding='utf-8',
    )
    file_handles.setFormatter(formatter)

    syslog = logging.StreamHandler()
    syslog.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    logger.addHandler(syslog)
    if not TESTING:
        logger.addHandler(file_handles)

    return logger


LOGGER = thiet_lap_logging(NAME)


def tam_ngung_den_khi(
        driver: Union[
            type(webdriver.Firefox),
            type(webdriver.Chrome),
        ],
        _xpath: AnyStr) -> Union[
            type(webdriver.Firefox),
            type(webdriver.Chrome),
        ]:
    '''Hàm tạm ngưng đến khi xuất hiện đường dẫn xpath
    '''
    _tam_ngung = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            _xpath,
        )),
    )
    return _tam_ngung


def tam_ngung_va_tim(driver, _xpath):
    '''Hàm tạm ngưng đến khi xuất hiện đường dẫn xpath và chọn xpath đó
    '''
    tam_ngung_den_khi(driver, _xpath)
    return driver.find_element(by='xpath', value=_xpath)


def chay_trinh_duyet(headless=True):
    '''Mở trình duyệt và trả về driver
    '''
    options = Options()
    options.headless = headless
    service = Service(GeckoDriverManager().install())
    LOGGER.info('Chạy trình duyệt, headless=%s', headless)
    _driver = webdriver.Firefox(
        options=options,
        service=service,
    )
    # Hàm đặt thời gian tải trang, dùng khi tải trang quá lâu
    # _driver.set_page_load_timeout(5)
    return _driver


def lay_sales(driver, url):
    filterLocation = input('Nhập vị trí muốn tìm: ')

    # Mở trang flash sale
    LOGGER.info('Lấy thông tin sales theo vị trí: %s', filterLocation)
    driver.get(url)

    # Lấy các khung giờ có sale
    xpath_khung_gio = '/html/body/div[1]/div/div[3]/div/div/div/div[3]/div/' \
        'div/div[1]/ul/li'
    tam_ngung_den_khi(driver, xpath_khung_gio)
    danh_sach_khung_gio = driver.find_elements(
        by='xpath',
        value=xpath_khung_gio,
    )
    list_promotion_id = []
    stt = 1
    for khung_gio in danh_sach_khung_gio:
        label = khung_gio.text
        label = label.replace('\n', ' - ')
        label = str(stt) + ': ' + label
        LOGGER.info(label)
        duong_dan = khung_gio.find_element(
            by='xpath',
            value='.//a',
        ).get_attribute('href')
        list_promotion_id.append([label, duong_dan.split('=')[-1]])
        stt += 1

    lua_chon = int(input('Nhập khung giờ muốn lấy: '))
    LOGGER.info('Đã lựa chọn: %s', list_promotion_id[lua_chon - 1][0])
    promotion_id = list_promotion_id[lua_chon - 1][-1]

    # Lấy category
    xpath_khung_cate= '/html/body/div[1]/div/div[3]/div/div/div/div[6]/div[1]'
    khung_cate = driver.find_element(
        by='xpath',
        value=xpath_khung_cate,
    )
    danh_sach_cate = khung_cate.find_elements(
        by='xpath',
        value='.//a',
    )
    xpath_nut_them = '/html/body/div[1]/div/div[3]/div/div/div/div[6]/div[1]/' \
        'div/div/div/div[1]'
    nut_them = driver.find_element(
        by='xpath',
        value=xpath_nut_them,
    )
    LOGGER.info('click nút thêm')
    nut_them.click()
    nut_them.click()
    LOGGER.info('lấy nút thêm')
    xpath_khung_cate_them = '/html/body/div[1]/div/div[3]/div/div/div/div[6]' \
        '/div[1]/div/div/div/div[2]/div/div/div/div'
    khung_cate_them = driver.find_element(
        by='xpath',
        value=xpath_khung_cate_them,
    )
    danh_sach_cate += khung_cate_them.find_elements(
        by='xpath',
        value='.//a',
    )
    stt = 1
    list_category_id = []
    list_label = []
    for category in danh_sach_cate:
        ten_cate = category.text
        label = str(stt) + ': ' + ten_cate
        LOGGER.info(label)
        duong_dan = category.get_attribute('href')
        category_id = re.search("(?<=categoryId=)\d+", duong_dan).group()
        list_category_id.append(category_id)
        list_label.append(label)
        stt += 1

    lua_chon_cate = int(input('Nhập danh mục muốn lấy: '))
    LOGGER.info('Đã lựa chọn danh mục: %s', list_label[lua_chon_cate - 1])
    category_id = list_category_id[lua_chon_cate - 1]

    # Lấy các sản phẩm đang sale tương ứng
    url_lay_tat_ca = 'https://shopee.vn/api/v2/flash_sale/get_all_itemids' \
        f'?need_personalize=true&promotionid={promotion_id}&sort_soldout=true'

    response = requests.get(url_lay_tat_ca)
    response = json.loads(response.content.decode('utf-8'))
    danh_sach_san_pham = response.get('data').get('item_brief_list')
    danh_sach_san_pham_id = []
    for san_pham in danh_sach_san_pham:
        danh_sach_san_pham_id.append(san_pham.get('itemid'))
    LOGGER.info('Tìm thấy %d sản phẩm', len(danh_sach_san_pham))

    # Đọc script
    with open('script.js', 'r') as tep_js:
        script_lay_item = tep_js.read()
    script_header = '''
    promoId = %s;
    catId = %s;
    filterLocation = '%s';
    itemId = %s;
    '''

    # Lấy danh sách sản phẩm ở khu vực cần tìm
    danh_sach_san_pham_o_gan = []

    LOGGER.info('Lấy thông tin các sản phẩm')
    for itemId in danh_sach_san_pham_id:
        # Lấy thông tin sản phẩm
        script_lay_item = script_header % (
            promotion_id,
            category_id,
            filterLocation,
            itemId,
        ) + script_lay_item
        thong_tin_san_pham = driver.execute_script(script_lay_item)
        thong_tin_san_pham = thong_tin_san_pham.get('data').get('items')[0]
        ten_san_pham = thong_tin_san_pham.get('name')
        dang_giam_gia = thong_tin_san_pham.get('discount')

        # Lấy thông tin shop
        shop_id = thong_tin_san_pham.get('shopid')
        url_thong_tin_shop = 'https://shopee.vn/api/v4/product/get_shop_info?' \
            f'shopid={shop_id}'
        response = requests.get(url_thong_tin_shop)
        response = json.loads(response.content.decode('utf-8'))
        thong_tin_shop = response.get('data')
        dia_chi = thong_tin_shop.get('place')
        # Kiểm tra location có trong địa chỉ thì lấy ra
        if filterLocation.lower() in dia_chi.lower():
            # Tạo đường dẫn sản phẩm và thêm vào danh sách
            url_san_pham = 'https://shopee.vn/--i.{shop_id}.{itemId}'
            danh_sach_san_pham_o_gan.append([
                ten_san_pham,
                dang_giam_gia,
                url_san_pham])

    # Hiển thị sản phẩm tìm được
    LOGGER.info(
        'Tìm thấy %d sản phẩm ở %s',
        len(danh_sach_san_pham_o_gan),
        filterLocation,
    )
    for san_pham in danh_sach_san_pham_o_gan:
        LOGGER.info(' - '.join(san_pham))
    return driver


def main():
    LOGGER.info('Chạy chương trình')

    LOGGER.info('Load tele config')
    CONFIG = ConfigParser()
    CONFIG.read('tele.conf')
    BOT_TELE = CONFIG.get('config', 'BOT_TELE')
    CHAT_ID = CONFIG.get('config', 'CHAT_ID')

    THOI_GIAN_HIEN_TAI = datetime.now()
    LOGGER.info('Gửi thông báo qua telegram')
    url = f'https://api.telegram.org/bot{BOT_TELE}/sendMessage'
    params = {
        'chat_id': CHAT_ID,
        'text': f'Chạy {NAME}: {THOI_GIAN_HIEN_TAI}',
    }
    requests.post(url=url, data=params)
    DRIVER = None

    try:
        DRIVER = chay_trinh_duyet(headless=False)
        DRIVER.maximize_window()
        SIZE = DRIVER.get_window_size()
        DRIVER.set_window_size(SIZE['width'] / 2, SIZE['height'])
        DRIVER.set_window_position(
            (SIZE['width'] / 2) + SIZE['width'],
            0,
            windowHandle='current',
        )

        DRIVER = lay_sales(DRIVER, url=URL)
        THOI_GIAN_XU_LY = datetime.now() - THOI_GIAN_HIEN_TAI
        LOGGER.info('Thời gian xử lý: %s', THOI_GIAN_XU_LY)
        return DRIVER
    except Exception as error:
        LOGGER.exception(error)
        return None


if __name__ == '__main__':
    web_driver = main()
    if web_driver:
        web_driver.quit()
