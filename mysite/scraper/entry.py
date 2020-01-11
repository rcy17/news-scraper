from scrapy.crawler import CrawlerProcess, CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor
from multiprocessing import Process
from threading import Thread
import subprocess
import search.models


def work():
    import os
    print('crawling start')
    '''process = CrawlerProcess(get_project_settings())
    process.crawl('tencent_nba')
    process.start()
    process.join()'''
    '''runner = CrawlerRunner(get_project_settings())
    d = runner.crawl('tencent_nba')

    # stop reactor when spider closes
    # d.addBoth(lambda _: reactor.stop())
    d.addBoth(lambda _: reactor.stop())

    reactor.run()  # the script will block here until the crawling is finished'''
    os.chdir('scraper')
    subprocess.run('scrapy crawl tencent_nba')
    os.chdir('..')
    print('crawling finished')
    search.models.FreqModel.update_news()
    Manager.change_state(False)


# it just provides static API
class Manager:
    working = False
    sub_thread = Thread(target=work)

    @staticmethod
    def is_working():
        return Manager.working

    @staticmethod
    def change_state(state=None):
        if state is None:
            Manager.working = not Manager.working
        else:
            Manager.working = state
        if Manager.working:
            # Manager.sub_process.start()
            Manager.sub_thread.start()
        return

