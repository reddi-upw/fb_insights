import scrapy
import scrapy_splash


def SplashRequest(url, callback, args=None, **kwargs):
    args = args or {}
    args.setdefault('timeout', 3600)
    return scrapy_splash.SplashRequest(
        url=url,
        callback=callback,
        args=args,
        **kwargs)


AUTH_LUA = """
function main(splash)
    splash:init_cookies(splash.args.cookies)
    assert(splash:go(splash.args.url))
    assert(splash:wait(0.5))
    splash:select('#email'):focus()
    assert(splash:wait(0.5))
    splash:send_text('{email}')
    assert(splash:wait(0.5))
    splash:select('#pass'):focus()
    assert(splash:wait(0.5))
    splash:send_text('{passwd}')
    assert(splash:wait(0.5))
    splash:send_keys('<Return>')
    assert(splash:wait(5))
    return {{
        cookies = splash:get_cookies(),
        html = splash:html()
    }}
end
"""


TUNE_INSIGHTS_LUA = """
function main(splash)
    splash:init_cookies(splash.args.cookies)
    assert(splash:go(splash.args.url))
    assert(splash:wait(10))
    local els = splash:select_all('._58al')
    els[4]:mouse_click()
    assert(splash:wait(5))
    return {
        cookies = splash:get_cookies(),
        html = splash:html()
    }
end
"""


INSIGHTS_URL = (
    'https://www.facebook.com/ads/audience-insights/people?'
    'act={adacc_id}&'
    'age=18-&'
    'country=US')


class InsightsSpider(scrapy.Spider):
    name = 'insights'

    def __init__(self, email, passwd, adacc_id, *args, **kwargs):
        super(InsightsSpider, self).__init__(*args, **kwargs)
        self.email = email
        self.passwd = passwd
        self.adacc_id = adacc_id
        print(email, passwd, adacc_id)

    def start_requests(self):
        urls = ('https://facebook.com',)
        lua_source = AUTH_LUA.format(email=self.email, passwd=self.passwd)
        for u in urls:
            yield SplashRequest(
                url=u,
                endpoint='execute',
                args={'lua_source': lua_source},
                callback=self.open_insights)

    def open_insights(self, response):
        yield SplashRequest(
            url=INSIGHTS_URL.format(adacc_id=self.adacc_id),
            endpoint='execute',
            args={'lua_source': TUNE_INSIGHTS_LUA},
            callback=self.parse_insights)

    def parse_insights(self, response):
        pass
