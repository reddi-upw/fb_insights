import time
import sys
import argparse
import json
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.common.keys import Keys


@contextmanager
def init_phantomjs_driver(headers=None, service_args=None, *args, **kwargs):
    headers = headers or {}
    service_args = service_args or []

    user_agent = (
        'Mozilla/5.0 (X11; Linux x86_64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/62.0.3202.62 Safari/537.36')
    default_headers = {
        # 'User-Agent': user_agent,
    }
    default_headers.update(headers)

    service_args.extend(['--ignore-ssl-errors=true', '--ssl-protocol=any'])

    dcap = webdriver.DesiredCapabilities.PHANTOMJS.copy()
    pref = 'phantomjs.page.customHeaders.'
    for k, v in default_headers.items():
        dcap[pref + k] = v

    driver = webdriver.PhantomJS(
        executable_path='/usr/bin/phantomjs',
        desired_capabilities=dcap,
        service_args=service_args)
    yield driver
    driver.quit()


def login(driver, email, password):
    LOGIN_URL = "https://facebook.com"
    EMAIL_INP_ID = 'm_login_email'
    PASSWORD_INP_ID = 'm_login_password'
    LOGIN_BTN_ID = 'u_0_5'
    CANCEL_BTN_XPATH = '//a[@role="button"]'

    driver.get(LOGIN_URL)
    email_el = driver.find_element_by_id(EMAIL_INP_ID)
    password_el = driver.find_element_by_id(PASSWORD_INP_ID)
    btn_el = driver.find_element_by_id(LOGIN_BTN_ID)
    email_el.send_keys(email)
    password_el.send_keys(password)
    btn_el.click()
    time.sleep(10)

    cancel_els = driver.find_elements_by_xpath(CANCEL_BTN_XPATH)
    if cancel_els:
        cancel_els[0].click()
        time.sleep(3)


def open_insights(driver):
    INSIGHTS_URL = 'https://www.facebook.com/ads/audience-insights/'
    CLOSE_BTN_XPATH = "//button[@title='Close']"

    driver.get(INSIGHTS_URL)
    time.sleep(5)

    btns = driver.find_elements_by_xpath(CLOSE_BTN_XPATH)
    if btns:
        btns[0].click()
        time.sleep(1)


def change_tab(driver, tab, subtab=None):
    TAB_XPATH = "//a[text()='{}']"

    tab_el = driver.find_element_by_xpath(TAB_XPATH.format(tab))
    tab_el.click()
    time.sleep(5)
    if subtab:
        subtab_el = driver.find_element_by_xpath(TAB_XPATH.format(tab))
        subtab_el.click()
        time.sleep(5)
    expand_all(driver)


def expand_all(driver):
    MORE_BTN_XPATH = "//button[text()='See More' or text()='See All']"

    while True:
        btns = driver.find_elements_by_xpath(MORE_BTN_XPATH)
        if not btns:
            break
        for btn in btns:
            btn.click()
            time.sleep(1)


def set_interest(driver, interest):
    INTEREST_INP_XPATH = "//input[@placeholder='Interest']"

    inp = driver.find_element_by_xpath(INTEREST_INP_XPATH)
    inp.send_keys(interest)
    time.sleep(1)
    inp.send_keys(Keys.ENTER)
    time.sleep(5)


def find_table_by_name(driver, name):
    el = driver.find_element_by_xpath("//div[text()='{}']".format(name))
    return find_closest_ancestor(el, ".//table")


def find_closest_ancestor(el, xpath):
    while not el.find_elements_by_xpath(xpath):
        parent = el.find_elements_by_xpath("./..")
        if not parent:
            return None
        el = parent[0]
    return el


def parse_table(table_el, headers=None):
    headers = [e.text for e in table_el.find_elements_by_xpath(".//th")]
    result = []
    for row_el in table_el.find_elements_by_xpath(".//tbody//tr"):
        row = [e.text for e in row_el.find_elements_by_xpath(".//td")]
        if headers:
            result.append(dict(zip(headers, row)))
        else:
            result.append(row)
    return result


def parse_category_table(table_el):
    result = []
    for row_el in table_el.find_elements_by_xpath(".//tbody//tr"):
        row = []
        for col_el in row_el.find_elements_by_xpath(".//td"):
            a_els = col_el.find_elements_by_xpath(".//a")
            if a_els:
                col = []
                for a_el in a_els:
                    col.append(
                        {'url': a_el.get_attribute('href'),
                         'value': a_el.text})
                row.append(col)
            else:
                row.append(col_el.text)
        result.append(row)
    return result


def parse(email, password, interest):
    result = {}
    with init_phantomjs_driver() as driver:
        login(
            driver=driver,
            email=email,
            password=password)
        open_insights(driver)
        set_interest(driver, interest)

        people = {}
        tab_name = 'Demographics'
        change_tab(driver, tab_name)
        for table_name in ('Lifestyle', 'Job Title'):
            table_el = find_table_by_name(driver, table_name)
            people[table_name] = parse_table(table_el)
        result[tab_name] = people

        interests = {}
        tab_name = 'Page Likes'
        change_tab(driver, tab_name)
        table_name = 'Top Categories'
        table_el = find_table_by_name(driver, table_name)
        parse_category_table(table_el)
        interests[table_name] = parse_table(table_el)
        result[tab_name] = interests

        geography = {}
        tab_name = 'Location'
        for subtab_name in ('Top Cities', 'Top Countries', 'Top Languages'):
            change_tab(driver, tab_name, subtab_name)
            table_el = driver.find_element_by_xpath('//table')
            geography[subtab_name] = parse_table(table_el)
        result[tab_name] = geography

        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--email', required=True)
    parser.add_argument('-p', '--password', required=True)
    parser.add_argument('-i', '--interest', required=True)
    parser.add_argument('-o', '--output', required=False)
    args = parser.parse_args()

    dumped = json.dumps(
        parse(
            email=args.email,
            password=args.password,
            interest=args.interest),
        indent=4)
    if args.output:
        with open(args.output, 'wb') as f:
            f.write(dumped)
    else:
        sys.stdout.write(dumped)
