from django.shortcuts import render, redirect
from .entry import Manager
from search.models import NewsModel, FreqModel, WordModel
from team.models import TeamModel, PlayerModel, RelationModel


def manage_scraper(request):
    from datetime import datetime
    start = datetime.now()
    news_count = NewsModel.objects.count()
    teams_count = TeamModel.objects.count()
    freq_count = FreqModel.objects.count()
    word_count = WordModel.objects.count()
    relation_count = RelationModel.objects.count()
    player_count = PlayerModel.objects.count()
    latest_time = NewsModel.objects.values('pub_time').order_by('-pub_time')[0]['pub_time']
    working = Manager.is_working()
    html_title = '爬虫管理'
    print(f'load manage cost {(datetime.now() - start).total_seconds()} seconds')
    return render(request, 'manage.html', locals())


def render_scraper(request):
    if request.method == 'POST':
        Manager.change_state()
    return redirect('/scraper')
