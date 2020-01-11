from django.db import models
from datetime import datetime
from django.db import transaction
import search.models


class RelationModel(models.Model):
    relation = models.FloatField(default=0)
    team = models.ForeignKey('TeamModel', on_delete=models.CASCADE)
    news = models.ForeignKey('search.NewsModel', on_delete=models.CASCADE)


class TeamModel(models.Model):
    related_news_id = {}
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=64)
    abbr = models.CharField(max_length=8)
    division = models.CharField(max_length=64)
    city = models.CharField(max_length=32)
    teamID = models.PositiveIntegerField(primary_key=True)

    def __str__(self):
        return self.tab(1)

    def tab(self, n):
        t = '    '
        return f'{self.code} {{\n' \
               f'{t * n}name: {self.name},\n' \
               f'{t * n}id: {self.teamID}\n' \
               f'{t * n}abbr: {self.abbr},\n' \
               f'{t * (n - 1)}}}'

    def get_related_news_ids(self):
        start = datetime.now()
        result = RelationModel.objects.filter(team=self).order_by('-news__pub_time').values_list('news_id', flat=True)
        print(f'get related news cost {(datetime.now() - start).total_seconds()} seconds')
        return result


class PlayerModel(models.Model):
    code = models.CharField(max_length=64)
    display_name = models.CharField(max_length=64)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    position = models.CharField(max_length=16)
    country = models.CharField(max_length=64)
    playerID = models.PositiveIntegerField(primary_key=True)
    height = models.FloatField()
    weight = models.CharField(max_length=32)
    team = models.ForeignKey(TeamModel, on_delete=models.CASCADE)

    def __str__(self):
        return self.tab(1)

    def tab(self, n):
        t = '    '
        return f'{self.code} {{\n' \
               f'{t * n}name: {self.display_name},\n' \
               f'{t * n}id:{self.playerID}\n' \
               f'{t * n}team: {self.team.tab(n + 1)},\n' \
               f'{t * (n - 1)}}}'

    @staticmethod
    def update_players():
        from pathlib import Path
        from json import load
        p = Path('scraper/static/teams')
        with transaction.atomic():
            for file in p.iterdir():
                data = load(open(str(file), 'r', encoding='utf-8'))["payload"]
                team_info = data['profile']
                team_id = int(team_info['id'])
                try:
                    team = TeamModel.objects.get(pk=team_id)
                except TeamModel.DoesNotExist:
                    # here add new team
                    team = TeamModel.objects.create(
                        code=team_info['code'],
                        name=team_info['name'],
                        abbr=team_info['abbr'],
                        division=team_info['division'],
                        city=team_info['city'],
                        teamID=team_id,
                    )
                for _info in data['players']:
                    player_info = _info['profile']
                    player_id = int(player_info['playerId'])
                    try:
                        player = PlayerModel.objects.get(pk=player_id)
                        player.team = team
                    except PlayerModel.DoesNotExist:
                        # here add new player
                        player = PlayerModel(
                            code=player_info['code'],
                            country=player_info['country'],
                            display_name=player_info['displayName'],
                            first_name=player_info['firstName'],
                            last_name=player_info['lastName'],
                            position=player_info['position'],
                            playerID=player_id,
                            height=player_info['height'],
                            weight=player_info['weight'],
                            team=team,
                        )
                    player.save()
        return


