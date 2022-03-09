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
    LOGGER.info('Lấy thông tin sales theo vị trí')
    driver.get(url)
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
        LOGGER.info(duong_dan)
        list_promotion_id.append([label, duong_dan.split('=')[-1]])
        stt += 1

    # lua_chon = int(input('Nhập khung giờ muốn lấy: '))
    lua_chon = 2
    promotion_id = list_promotion_id[lua_chon - 1]
    LOGGER.info(list_promotion_id[lua_chon - 1])

    url_lay_tat_ca = 'https://shopee.vn/api/v2/flash_sale/get_all_itemids' \
        f'?need_personalize=true&promotionid={promotion_id}&sort_soldout=true'
    url_thong_tin_shop = 'https://shopee.vn/api/v4/product/get_shop_info?' \
        f'shopid={shop_id}'
    shop_id = 131666219

    script_lay_item = r'''
    promoId = %s;
    catId = %s;
    filterLocation = '%s';
    itemId = %s;
    return fetch(
    "https://shopee.vn/api/v2/flash_sale/flash_sale_batch_get_items", {
      "headers": {
        "accept": "application/json",
        "accept-language": "vi",
        "content-type": "application/json",
        "if-none-match-": "55b03-c9b9fb25684b2b06733c64898f2b3197",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-api-source": "rweb",
        "x-csrftoken": "A0O24HgbOXbamkLtd1BV8OVFrcXOwzjY",
        "x-kl-ajax-request": "Ajax_Request",
        "x-requested-with": "XMLHttpRequest",
        "x-shopee-language": "vi"
      },
      "referrer": "https://shopee.vn/flash_sale?categoryId="+catId+"&promotionId="+promoId,
      "referrerPolicy": "no-referrer-when-downgrade",
      "body": "{\"promotionid\":"+promoId+",\"categoryid\":"+catId+",\"itemids\":["+itemId+"],\"sort_soldout\":false,\"limit\":1,\"need_personalize\":true,\"with_dp_items\":true}",
      "method": "POST",
      "mode": "cors",
      "credentials": "include"
    }).then(res => res.json());
    '''

    # Đọc tệp js
    with open('script.js', 'r') as tep_js:
        promoId = list_promotion_id[lua_chon - 1][-1]
        catId = 12
        filterLocation = 'TP. Hồ Chí Minh'
        itemId = 11009435571
        script = tep_js.read()
        script = script % (
            promoId,
            catId,
            filterLocation,
        )
    LOGGER.info(script)

    # Chạy script
    result = driver.execute_script(script_lay_item % (
            promoId,
            catId,
            filterLocation,
            itemId,
    ))
    LOGGER.info(result)
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
