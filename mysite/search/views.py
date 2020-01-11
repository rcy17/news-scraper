from django.shortcuts import render, Http404, redirect
from .models import NewsModel, FreqModel, RelationModel
from django.core.paginator import Paginator
from utils.parser import TextExtractor
from datetime import datetime


def search_start(request):
    start = datetime.now()
    model_news = NewsModel.get_latest_news(5)
    paginator = Paginator(model_news, 5)
    page = request.GET.get('page', 1)
    result = paginator.get_page(page)
    params = {
        'page_news': result,
        'html_title': '新闻搜索系统'
    }
    print(f'load search start cost {(datetime.now() - start).total_seconds()} seconds')
    return render(request, 'search/search.html', params)


def search_target(request):
    if request.method != 'GET':
        raise Http404()
    key_word = request.GET.get('keyword')
    if not key_word:
        return redirect('/')
    abstracts, cost, tags = FreqModel.query(key_word)
    paginator = Paginator(abstracts, 5)
    page = request.GET.get('page', 1)
    result = paginator.get_page(page)
    page_news = []
    for news_id, factor in result:
        page_news.append(NewsModel.objects.get(pk=news_id).to_abstract(tags))
    params = {
        'result': result,
        'keyword': key_word,
        'page_news': page_news,
        'cost': cost.total_seconds(),
        'total': len(abstracts),
        'html_title': f'{key_word}_搜索结果',
        'other_string': f'keyword={key_word}&'
    }
    return render(request, 'search/search.html', params)


def show_news(response, news_id):
    start = datetime.now()
    news = NewsModel.objects.get(pk=news_id)
    news.change_for_html()
    params = {
        'news': news,
    }
    print(f'load news cost {(datetime.now() - start).total_seconds()} seconds in total')
    return render(response, 'search/news.html', params)
