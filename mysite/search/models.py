from django.db import models
from django.db import transaction
from django.db.models import Sum
from team.models import TeamModel, PlayerModel, RelationModel
from scraper.entry import Manager
import jieba
import jieba.analyse
from pathlib import Path
from json import load
from datetime import datetime, timedelta

# stop_words = set()
MAX_CONTENT_LENGTH = 100
TIME_REPORT_FORMAT = "%H:%M:%S:%f"

STOP_WORD_INITIALIZED = False
if not STOP_WORD_INITIALIZED:
    STOP_WORD_INITIALIZED = True
    jieba.analyse.set_stop_words("utils/stop_words.txt")
    jieba.analyse.set_idf_path("utils/idf.txt")


class WordModel(models.Model):
    word = models.CharField(max_length=32, primary_key=True, unique=True)
    # warning: this relationship is unclear, i don't know if two players will have same word
    related_team = models.ForeignKey(TeamModel, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.word

    @staticmethod
    def update_words():
        p = Path('scraper/static/teams')
        alias_info = load(open(p.parent.joinpath('alias.json'), 'r', encoding='utf-8'))
        player_manager = PlayerModel.objects
        team_manager = TeamModel.objects
        word_manager = WordModel.objects
        important_word = []
        # add alias first
        for key, value in alias_info.items():
            alias = value.get('alias')
            if alias is None:
                continue
            try:
                player = player_manager.get(code=key)
            except PlayerModel.DoesNotExist:
                # no such player in database
                continue
            for each in alias:
                important_word.append((each, True))
                if word_manager.filter(word=each).exists():
                    continue
                word_manager.create(
                    word=each,
                    related_team=player.team,
                )
        # add player name
        for player in player_manager.all():
            first_name = player.first_name
            last_name = player.last_name
            names = [first_name, last_name, first_name + last_name]
            for name in names:
                important_word.append((name, True))
                try:
                    word_manager.get(word=name)
                except WordModel.DoesNotExist:
                    word_manager.create(word=name, related_team=player.team)
        # add team name
        for team in team_manager.all():
            important_word.append((team.name, False))
            try:
                word = word_manager.get(word=team.name)
                if word.related_team == team.pk:
                    continue
                word.related_team = team
                word.save()
            except WordModel.DoesNotExist:
                word_manager.create(word=team.name, related_team=team)

        # set jieba dict
        for word, is_player in important_word:
            if is_player:
                jieba.add_word(word, 100, 'nr')
            else:
                jieba.add_word(word, 200, 'nt')

        return


class NewsModel(models.Model):
    title = models.CharField(max_length=256)
    pub_time = models.DateTimeField(null=True)
    source = models.CharField(max_length=64, null=True)
    content = models.TextField()
    text = models.TextField(null=True, default='')
    newsID = models.BigIntegerField(primary_key=True)
    related_teams = models.ManyToManyField(TeamModel, through='team.RelationModel')
    contain_words = models.ManyToManyField(WordModel, through='FreqModel')

    @staticmethod
    def get_latest_news(n):
        day = 0
        numbers = 0
        while numbers < n:
            day += 1
            numbers = NewsModel.objects.filter(pub_time__gt=datetime.now() - timedelta(days=day)).order_by(
                '-pub_time').count()
        all_news = NewsModel.objects.filter(pub_time__gt=datetime.now() - timedelta(days=day)).order_by('-pub_time')[:n]
        result = [NewsModel.to_abstract(news, []) for news in all_news]
        return result

    def to_abstract(self, tags):
        data = self.text
        title = self.title
        first_occur = -1
        for tag in tags:
            title = title.replace(tag, f'<em>{tag}</em>')
            occur = data.find(tag)
            if occur > -1:
                first_occur = occur if occur < first_occur or first_occur < 0 else first_occur

        if len(data) > MAX_CONTENT_LENGTH and first_occur > 5:
            data = '...' + data[first_occur - 5:]
        if len(data) > MAX_CONTENT_LENGTH:
            data = data[:MAX_CONTENT_LENGTH] + '...'

        for tag in tags:
            data = data.replace(tag, f'<em>{tag}</em>')
            title = title.replace(tag, f'<em>{tag}</em>')
        self.content = data
        self.title = title
        return self

    def change_for_html(self):
        team_ids = self.related_teams.values_list('teamID', flat=True)
        content = self.content
        for team_id in team_ids:
            team_words = WordModel.objects.filter(related_team_id=team_id)
            occur_words = self.contain_words.values('word').intersection(team_words)
            url = f'/team/{team_id}'
            for word_dict in occur_words:
                word = word_dict['word']
                content = content.replace(word, f'<a href={url}>{word}</a>')
        self.content = content
        return


class FreqModel(models.Model):
    freq = models.FloatField()
    news = models.ForeignKey(NewsModel, on_delete=models.CASCADE)
    word = models.ForeignKey(WordModel, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.occur}: {str(self.news_id)}--{self.team.name if self.team else str(self.word)}'

    @staticmethod
    @transaction.atomic
    def initialize_news():
        print(f'{datetime.now().strftime(TIME_REPORT_FORMAT)} start update_words')
        WordModel.update_words()
        print(f'{datetime.now().strftime(TIME_REPORT_FORMAT)} finish update_words')
        # now we really start to update news
        news_manager = NewsModel.objects
        word_manager = WordModel.objects
        freq_manager = FreqModel.objects
        related_manager = RelationModel.objects
        directory = Path('scraper/static/info')
        new_file_list = []
        for path in directory.iterdir():
            news_id = int(path.stem)
            if not news_manager.filter(pk=news_id).exists():
                new_file_list.append(path)

        print(f'{datetime.now().strftime(TIME_REPORT_FORMAT)} finish directory filter')
        news_count = len(new_file_list)
        # ready to  add relations
        new_freq = []
        new_relation = []

        # flush bulks above
        def flush(bulk, manager):
            while len(bulk) > 999:
                manager.bulk_create(bulk[:999])
                bulk = bulk[999:]
            return bulk

        for index, path in enumerate(new_file_list):
            start_time = datetime.now()
            print(f'{start_time.strftime(TIME_REPORT_FORMAT)} start No.{index}')
            news_id = int(path.stem)
            # parser this news and add into database
            info = load(open(str(path), 'r', encoding='utf-8'))
            data = info['text']
            NewsModel.objects.create(
                title=info['title'],
                source=info['source'],
                pub_time=info['time'],
                content=info['content'],
                newsID=news_id,
                text=data
            )

            new_words = []
            slice_result = jieba.analyse.extract_tags(data, 999, True)
            # first add all new words
            for slice_word, freq in slice_result:
                if not word_manager.filter(word=slice_word).exists():
                    new_words.append(WordModel(word=slice_word))
            word_manager.bulk_create(new_words)

            team_freq = {}
            for slice_word, freq in slice_result:
                word = word_manager.get(word=slice_word)
                new_freq.append(FreqModel(
                    news_id=news_id,
                    word_id=word.pk,
                    freq=freq,
                ))

                if word.related_team:
                    team_freq.setdefault(word.related_team, 0)
                    team_freq[word.related_team] += freq

            for team, freq in team_freq.items():
                new_relation.append(RelationModel(
                    relation=freq,
                    news_id=news_id,
                    team=team,
                ))
            new_freq = flush(new_freq, freq_manager)
            new_relation = flush(new_relation, related_manager)
            print(f'{index} / {news_count} cost {(datetime.now() - start_time).total_seconds()} seconds')
        freq_manager.bulk_create(new_freq)
        related_manager.bulk_create(new_relation)
        return

    @staticmethod
    def update_news():
        start = datetime.now()
        print(f'{start.strftime(TIME_REPORT_FORMAT)} start update news')

        news_manager = NewsModel.objects
        word_manager = WordModel.objects
        freq_manager = FreqModel.objects
        related_manager = RelationModel.objects
        directory = Path('scraper/static/info')
        new_file_list = []
        for path in directory.iterdir():
            news_id = int(path.stem)
            if not news_manager.filter(pk=news_id).exists():
                new_file_list.append(path)
        cnt = 0
        for index, path in enumerate(new_file_list):
            if not Manager.is_working():
                print('end update forcefully!')
                break
            with transaction.atomic():
                news_id = int(path.stem)
                # parser this news and add into database
                info = load(open(str(path), 'r', encoding='utf-8'))
                data = info['text']
                NewsModel.objects.create(
                    title=info['title'],
                    source=info['source'],
                    pub_time=info['time'],
                    content=info['content'],
                    newsID=news_id,
                    text=data
                )

                new_words = []
                slice_result = jieba.analyse.extract_tags(data, 999, True)
                # first add all new words
                for slice_word, freq in slice_result:
                    if not word_manager.filter(word=slice_word).exists():
                        new_words.append(WordModel(word=slice_word))
                word_manager.bulk_create(new_words)

                team_freq = {}
                new_freq = []
                new_relation = []
                for slice_word, freq in slice_result:
                    word = word_manager.get(word=slice_word)
                    new_freq.append(FreqModel(
                        news_id=news_id,
                        word_id=word.pk,
                        freq=freq,
                    ))

                    if word.related_team:
                        team_freq.setdefault(word.related_team, 0)
                        team_freq[word.related_team] += freq

                for team, freq in team_freq.items():
                    new_relation.append(RelationModel(
                        relation=freq,
                        news_id=news_id,
                        team=team,
                    ))

                freq_manager.bulk_create(new_freq)
                related_manager.bulk_create(new_relation)
            cnt += 1
        print(f'update {cnt} news finish after {(datetime.now() - start).total_seconds()} seconds!')
        return

    @staticmethod
    def query(key_word):
        start = datetime.now()
        tags = dict(jieba.analyse.extract_tags(key_word, 20, True))
        words = WordModel.objects.filter(word__in=tags.keys())
        # get weight dict to reduce hash time
        weight = {word.pk: tags[word.word] for word in words}
        news_freq = {}
        for word in words:
            freq_news_list = FreqModel.objects.filter(word=word).values_list('freq', 'news')
            for freq, news_id in freq_news_list:
                news_freq.setdefault(news_id, 0)
                news_freq[news_id] += freq * weight[word.pk]

        result = sorted(news_freq.items(), key=lambda x: x[1], reverse=True)
        stop = datetime.now()
        delta = stop - start
        print(f'query cost {delta.total_seconds()} seconds')
        return result, delta, tags

    @staticmethod
    def get_rank():
        start = datetime.now()
        teams = TeamModel.objects.values_list('teamID', 'name')
        team_to_info = {
            team_id: {
                'count': RelationModel.objects.filter(team_id=team_id).count(),
                'factor': RelationModel.objects.filter(team_id=team_id).aggregate(Sum('relation'))['relation__sum'],
                'name': name
            } for team_id, name in teams
        }
        print(f'cost {(datetime.now() - start).total_seconds()} seconds to get rank')
        return team_to_info
