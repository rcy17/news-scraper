from django.shortcuts import render
from search.models import FreqModel, RelationModel, NewsModel
from .models import TeamModel, PlayerModel
from django.core.paginator import Paginator
from datetime import datetime
from pathlib import Path
RANK_PER_PAGE = 10
RELATED_PER_PAGE = 20


def show_team(request, team_id):
    start = datetime.now()

    team = TeamModel.objects.get(pk=team_id)
    all_news = team.get_related_news_ids()
    paginator = Paginator(all_news, RELATED_PER_PAGE)
    page = request.GET.get('page', 1)
    # warning: this result is just news_ids
    result = paginator.get_page(page)
    related_news = []
    for news_id in result:
        related_news.append(NewsModel.objects.get(pk=news_id))
    players = PlayerModel.objects.filter(team_id=team.pk)
    for player in players:
        path = f"/static/png/{player.pk}.png"
        if Path('scraper' + path).exists():
            player.img = path
        else:
            player.img = '/static/svg/not_found.svg'

    params = {
        'html_title': team.name + '队主页',
        'players': players,
        'team': team,
        'related_news': related_news,
        'result': result,
        'count': len(all_news),
    }
    print(f'cost {(datetime.now() - start).total_seconds()} seconds')
    return render(request, 'team.html', params)


def show_rank(request, rank_key):
    rank_dict = FreqModel.get_rank()
    rank_list = sorted([{
        'team_id': team_id,
        'count': data['count'],
        'name': data['name'],
        'factor': data['factor']
    } for team_id, data in rank_dict.items()], key=lambda x: x[rank_key], reverse=True)

    for index, d in enumerate(rank_list):
        # rank should begin with 1 instead of 0
        d['rank'] = index + 1

    first_ten = rank_list[0: 10]
    middle_ten = rank_list[10: 20]
    last_ten = rank_list[20:]
    params = {
        'html_title': f"球队{'热度' if rank_key == 'factor' else '知名'}榜",
        'first_ten': first_ten,
        'middle_ten': middle_ten,
        'last_ten': last_ten
    }
    return render(request, f"rank_{rank_key}.html", params)

