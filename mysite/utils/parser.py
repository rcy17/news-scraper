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


if __name__ == '__main__':
    '''from pathlib import Path
    from json import *
    p = Path('../scraper/static/info')
    e = TextExtractor()
    for file in p.iterdir():
        e.reset()
        data = load(open(str(file), encoding='utf-8'))
        e.feed(data['content'])
        data['text'] = e.get_data()
        dump(data, open(str(file), 'w', encoding='utf-8'), ensure_ascii=False)
    print(e.get_data())'''

    def f():
        from time import sleep
        sleep(3)
        print('done')
    from threading import Thread
    print('go')
    t = Thread(target=f)
    t.start()
    t.join()
    print('start')

