import os
import base64

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
function expand_all(splash)
    local cond = true
    while cond do
        cond = false
        local buts = splash:select_all('._5xp8')
        for _, but in ipairs(buts) do
            local t = but:text()
            if t == 'See More' or t == 'See All' then
                cond = true
                but:mouse_click()
                assert(splash:wait(1))
              end
        end
    end
end

function find_element(splash, class, attr_name, attr_value)
    local els = splash:select_all(class)
    for _, el in pairs(els) do
        if el ~= nil then
            local ph = el:info().attributes[attr_name]
            if ph ~= nil then
                if ph:lower() == attr_value:lower() then
                    return el
                end
            end
        end
    end
end

function main(splash)
    splash:init_cookies(splash.args.cookies)
    assert(splash:go(splash.args.url))
    assert(splash:wait(10))
    local fe = find_element(splash, '._58al', 'placeholder', 'interest')
    fe:send_text('{interest}')
    assert(splash:wait(5))
    fe:send_keys('<Return>')
    assert(splash:wait(5))
    expand_all(splash)
    assert(splash:wait(1))
    return {{
        cookies = splash:get_cookies(),
        html = splash:html(),
        png = splash:png()
    }}
end
"""


TUNE_GEOGRAPHY_LUA  = """
function expand_all(splash)
    local cond = true
    while cond do
        cond = false
        local buts = splash:select_all('._5xp8')
        for _, but in ipairs(buts) do
            local t = but:text()
            if t == 'See More' or t == 'See All' then
                cond = true
                but:mouse_click()
                assert(splash:wait(1))
            end
        end
    end
end

function find_element(splash, class, attr_name, attr_value)
    local els = splash:select_all(class)
    for _, el in pairs(els) do
        if el ~= nil then
            local ph = el:info().attributes[attr_name]
            if ph ~= nil then
                if ph:lower() == attr_value:lower() then
                    return el
                end
            end
        end
    end
end

function main(splash)
    splash:init_cookies(splash.args.cookies)
    assert(splash:go(splash.args.url))
    assert(splash:wait(10))
    local fe = find_element(splash, '._5nwp', 'title', '{subtab}')
    fe:mouse_click()
    assert(splash:wait(5))
    expand_all(splash)
    assert(splash:wait(1))
    return {{
        cookies = splash:get_cookies(),
        html = splash:html(),
        png = splash:png()
    }}
end
"""


INSIGHTS_URL = (
    'https://www.facebook.com/ads/audience-insights/{tab}?'
    'act={adacc_id}&'
    'age=18-&'
    'country=US')


def parse_table(table):
    result = []
    headers = [h.extract() for h in table.xpath('//th//text()')]
    w = len(headers)
    tr = []
    for n, td in enumerate(table.xpath('//td//text()')):
        tr.append(td.extract())
        if (n + 1) % w == 0:
            result.append(dict(zip(headers, tr)))
            tr = []
    return result


class InsightsSpider(scrapy.Spider):
    name = 'insights'

    def __init__(self, email, passwd, adacc_id, interest, screen,
                 *args, **kwargs):
        super(InsightsSpider, self).__init__(*args, **kwargs)
        self.email = email
        self.passwd = passwd
        self.adacc_id = adacc_id
        self.interest = interest
        self.screen = screen

    def start_requests(self):
        urls = ('https://facebook.com',)
        lua_source = AUTH_LUA.format(email=self.email, passwd=self.passwd)
        cb = lambda resp: self.open_insights(resp, 'geography')
        for u in urls:
            yield SplashRequest(
                url=u,
                endpoint='execute',
                args={'lua_source': lua_source},
                callback=cb)

    def open_insights(self, response, tab):
        lua_source = TUNE_INSIGHTS_LUA.format(interest=self.interest)
        url = INSIGHTS_URL.format(adacc_id=self.adacc_id, tab=tab)

        if tab == 'geography':
            yield SplashRequest(
                url=url,
                endpoint='execute',
                args={'lua_source': lua_source},
                callback=self.parse_geography_insights)

            st1 = 'Top Countries'
            cb = lambda r: self.parse_geography_insights(r, st1)
            yield SplashRequest(
                url=url,
                endpoint='execute',
                args={'lua_source': TUNE_GEOGRAPHY_LUA.format(subtab=st1)},
                callback=cb)

            st2 = 'Top Languages'
            cb = lambda r: self.parse_geography_insights(r, st2)
            yield SplashRequest(
                url=url,
                endpoint='execute',
                args={'lua_source': TUNE_GEOGRAPHY_LUA.format(subtab=st2)},
                callback=cb)

    def parse_geography_insights(self, response, subtab='Top Cities'):
        bn = os.path.basename(self.screen)
        n, e = os.path.splitext(bn)
        dn = os.path.dirname(self.screen)
        output = os.path.join(
            dn,
            '{}_{}{}'.format(n, '_'.join(subtab.split(' ')), e))

        d = base64.b64decode(response.data['png'])
        with open(output, 'wb') as f:
            f.write(d)

        table = response.xpath('//table')
        yield {subtab: parse_table(table)}
