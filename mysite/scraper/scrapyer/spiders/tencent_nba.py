import scrapy
import re
from pathlib import Path
from json import loads, dump
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    ignore_tag = {'script', 'style'}

    def __init__(self):
        super().__init__()
        self.data = ''
        self.script = 0

    def handle_starttag(self, tag, attrs):
        self.script += tag in TextExtractor.ignore_tag

    def handle_endtag(self, tag):
        self.script -= tag in TextExtractor.ignore_tag

    def handle_data(self, data):
        if not self.script:
            self.data += data

    def get_data(self):
        return self.data.replace('\n', '')

    def reset(self):
        super().reset()
        self.data = ''
        self.script = 0


class TencentNBASpider(scrapy.Spider):
    name = "tencent_nba"

    def start_requests(self):
        # this is a useful json from tencent
        # reference = 'https://mat1.gtimg.com/sports/nba2015_statics/data/nba_player_ids.json'
        # yield scrapy.Request(url=reference, callback=self.get_alias)

        Path('static/news/').mkdir(exist_ok=True)
        base_url = 'https://sports.qq.com/l/basket/nba/list20181018164449%s.htm'
        urls = [base_url % ('_' + str(i)) for i in range(2, 3)]
        urls.insert(0, base_url % '')
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        for html in re.findall(r",url:'(.*?)'", response.css('div script').get()):
            file = Path('static/info/' + (''.join(html.split('/')[-2:])).split('.')[0] + '.json')
            if file.exists():
                break
            yield scrapy.Request(url=html, callback=self.parse_news)

    def parse_news(self, response):
        def get_json():
            data = dict()
            data['title'] = response.css('h1::text').get()
            data['source'] = response.css('span.a_source a::text').get()
            data['time'] = response.css('span.a_time::text').get()
            raw_content = ''.join(response.css('div.Cnt-Main-Article-QQ p').getall())
            data['content'] = raw_content.replace(r'img src="//', r'img src="https://')
            parser = TextExtractor()
            parser.feed(raw_content)
            data['text'] = parser.get_data()
            return data

        raw_data = response.css('div.qq_article').get()
        # full news should far more than 256 bytes
        if len(raw_data) < 256:
            return
        info_directory = Path('static/info')
        news_directory = Path('static/news')
        filename = (''.join(response.url.split('/')[-2:])).split('.')[0] + '.json'
        info = get_json()
        with open(info_directory.joinpath(filename), 'w', encoding='utf-8') as fp:
            dump(info, fp, ensure_ascii=False)
        # with open(news_directory.joinpath(filename), 'w', encoding='utf-8') as fp:
        #     fp.write(raw_data)

    def get_alias(self, response):
        s = response.body.decode('gbk').replace('\n', '')
        data = loads(re.search(r'{.*}', s).group())
        with open('static/alias.json', 'w', encoding='utf-8') as fp:
            dump(data, fp, ensure_ascii=False)


class NBAInfoSpider(scrapy.Spider):
    name = "nba_info"

    def start_requests(self):
        Path('static/teams/').mkdir(exist_ok=True)
        Path('static/img/').mkdir(exist_ok=True)
        yield scrapy.Request('https://china.nba.com/teamindex/', callback=self.parse)

    def parse(self, response):
        base = 'https://china.nba.com/static/data/team/roster_%s.json'
        for name in response.css('div.footer li a::attr(href)').getall():
            yield scrapy.Request(base % (name.replace('/', '')), callback=self.parse_team)

    def parse_team(self, response):
        team_name = response.url.split('_')[-1].split('.')[0]
        data = loads(response.text)
        p = Path('static/teams/')
        p.mkdir(exist_ok=True)
        with open(p.joinpath(team_name + '.json'), 'w', encoding='utf-8') as fp:
            dump(data, fp, ensure_ascii=False)

        logo = 'https://china.nba.com/media/img/teams/logos/%s_logo.svg'
        if not Path('static/svg/%s_logo.svg').exists():
            yield scrapy.Request(logo % data['payload']['profile']['abbr'], callback=self.load_img)

        base = 'https://china.nba.com/media/img/players/head/260x190/%s.png'
        for player in data['payload']['players']:
            if Path('static/img/%s.png' % player['profile']['playerId']).exists():
                continue
            yield scrapy.Request(base % player['profile']['playerId'], callback=self.load_img)

    def load_img(self, response):
        file_name = response.url.split('/')[-1]
        data = response.body
        # real image should far more than 2KB
        if len(data) < 2048:
            return
        with open('static/' + file_name.split('.')[1] + '/' + file_name, 'wb') as fp:
            fp.write(response.body)


class NBAParser(scrapy.Spider):
    name = "nba_parser"

    # warning: this parser should be removed after debugging

    def start_requests(self):
        from pathlib import Path
        directory = 'D:/repository/hw3/mysite/scraper/static/news'
        prefix = 'http://127.0.0.1:8000/2017/'
        Path('static/info').mkdir(exist_ok=True)
        for p in Path(directory).iterdir():
            yield scrapy.Request(url=prefix + p.name, callback=self.parse)

    def parse(self, response):
        def get_json():
            data = dict()
            data['title'] = response.css('h1::text').get()
            data['source'] = response.css('span.a_source a::text').get()
            data['time'] = response.css('span.a_time::text').get()
            raw_content = ''.join(response.css('div.Cnt-Main-Article-QQ p').getall())
            data['content'] = raw_content.replace(r'img src="//', r'img src="https://')
            return data
        directory = Path('static/info')
        filename = response.url.split('/')[-1].split('.')[0] + '.json'
        info = get_json()
        with open(directory.joinpath(filename), 'w', encoding='utf-8') as fp:
            dump(info, fp, ensure_ascii=False)

