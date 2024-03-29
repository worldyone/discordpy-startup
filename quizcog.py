import discord
from discord.ext import commands
import random
import wikipedia
import requests
import urllib
from bs4 import BeautifulSoup as bs4


class QuizCog(commands.Cog):
    """
    クイズボット
    """

    wikipedia.set_lang("ja")

    wikipedia_page = None
    wordlist = []

    @commands.group(aliases=['q'])
    async def quiz_wikipedia(self, ctx):
        """wikipedia問題"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="wikipediaクイズ機能",
                description="wikipediaクイズ機能の使い方です。"
            )

            embed.add_field(
                name="game", value="wikipediaクイズをする\n        e.q game", inline=False)
            embed.add_field(
                name="prepare", value="ランダム単語の単語帳を作成する\n        e.q prepare", inline=False)
            embed.add_field(
                name="next", value="単語帳から一問出題する\n        e.q next", inline=False)
            embed.add_field(
                name="answer [, True]",
                value="取得中のwikipediaページのタイトルを表示する\nTrueをつけると隠し文字で表示する\n        e.q answer", inline=False)
            embed.add_field(
                name="hint [pv|category|url|word 'N'|summary [|1|2]", value="現在取得しているwikipediaページの情報を出す\n        e.q hint sentence", inline=False)
            embed.add_field(
                name="find 'xxxx'", value="指定した単語のwikipediaのページを取得する\n        e.q find 'target-word'", inline=False)
            embed.add_field(
                name="get", value="wikipediaからランダムなページを取得する\n        e.q get", inline=False)

            await ctx.send(embed=embed)

    @quiz_wikipedia.command(aliases=['game'])
    async def play_wikipedia_quiz_easy(self, ctx, need_pv = 200):
        pv = 0
        ttl = 5
        while True:
            ttl -= 1
            await self.get_random_wikipedia_page(ctx)
            pv = int(str(self.get_pv()).replace(",", ""))
            if pv > need_pv:
                await ctx.send("妹「良い問題を見つけたよ！」")
                break
            if ttl <= 0:
                await ctx.send("妹「だけど、あんまり良い問題じゃないかも…。」")
                await ctx.send(self.wikipedia_page.title)
                await ctx.send("妹「全然良い問題見つかられなかった…。ごめんね、お兄ちゃん...」")
                return
            await ctx.send("妹「だけど、あんまり良い問題じゃないかも…。もう一度探してくるね！」")
            await ctx.send(self.wikipedia_page.title)

        await ctx.send("妹「サマリーを答えを伏字で読み上げるから分かったら答えてね！」\n ----")
        await self.print_hint(ctx, 'summary', 1)
        await self.print_hint(ctx, 'pv')
        await ctx.send("妹「答えを内緒で教えるね！」")
        await self.print_answer(ctx, spoiler=True)

    @quiz_wikipedia.command(aliases=['get'])
    async def get_random_wikipedia_page(self, ctx):
        """wikipediaからランダムな記事を一つ取得する"""

        await ctx.send("妹「wikipediaからランダムな記事を取ってくるね！」")
        await ctx.send("妹は中空に手を翳し、何かを掴むような動作をしている。")

        # 日本語wikipediaからランダムな単語を一つ決めてページを取得する
        while True:
            try:
                self.wikipedia_page = wikipedia.page(wikipedia.random())
                break
            except wikipedia.exceptions.DisambiguationError as e:
                # 曖昧さ回避のページを取得してしまった場合
                continue
        await ctx.send("妹「ランダムな記事を取ってきたよ！」")

    def do_hide_words(self, s: str, mask_word: str = "**ANSWER**"):
        """答えがそのまま記載されている場合が多いので、マスクする"""

        hide_words = [self.wikipedia_page.title]
        space_word = s[:s.find("（")]
        hide_words.append(space_word)
        hide_words.append(
            self.wikipedia_page.title.replace(" ", ""))  # 「霧雨 魔理沙」を「霧雨魔理沙」でもヒットするように
        # 「Python（パイソン）は、...」の「パイソン」を取得する
        # 「ウォルト・ディズニー（Walt Disney, 1901年12月5日 - 1966年12月15日）...」とある場合、日付は削除したくないので句読点で避ける
        punctuation_mark = [",", "、"]
        start_parentheses = s.find("（")
        end_parentheses = s.find("）")
        end_para = end_parentheses
        for mark in punctuation_mark:
            mark_position = s.find(mark)
            if start_parentheses < mark_position < end_parentheses:
                end_para = mark_position
        para_title = s[s.find("（") + 1: end_para]
        hide_words.append(para_title)

        # **ANSWER**でマスクする
        for hide_word in hide_words:
            s = s.replace(hide_word, mask_word)
        return s

    @quiz_wikipedia.command(aliases=['answer', 'title'])
    async def print_answer(self, ctx, spoiler=False):
        """答え表示"""
        await ctx.send(f'妹「答えは「**{"||"*spoiler}{self.wikipedia_page.title}{"||"*spoiler}**」だよ！」')

    @quiz_wikipedia.command(aliases=['find', 'page'])
    async def get_wikipedia_page(self, ctx, target_word: str):
        """指定した単語のwikipediaページを取得する"""
        try:
            self.wikipedia_page = wikipedia.page(target_word)
        except wikipedia.exceptions.DisambiguationError as e:
            await ctx.send("妹「あっ、書き損じしちゃってた…。」妹は消しゴムを取り出した。")
            self.wikipedia_page = None
            return
        await ctx.send("妹「調べてきたよ！お兄ちゃん！」")

    @quiz_wikipedia.command(aliases=['hint'])
    async def print_hint(self, ctx, key: str, op: int = 0):
        if not self.wikipedia_page:
            return
        if key.startswith("word"):
            word_position = int(key[len('word'):])
            await ctx.send(f'妹「{word_position}文字目は「{self.wikipedia_page.title[word_position - 1]}」だよ！」')
        if key == "summary":
            if op == 0:
                # サマリーをすべて表示
                summary = self.wikipedia_page.summary
                question_sentence = self.do_hide_words(summary)
                await ctx.send(question_sentence)
            elif op == 1:
                # サマリーの一行目を表示
                s = self.wikipedia_page.summary  # サマリーを取得する
                one_line = s[:s.find("\n")]  # 最初の改行が来るまでを取得する
                question_sentence = self.do_hide_words(one_line)
                await ctx.send(question_sentence)
            elif op == 2:
                # サマリーの二行目を表示
                se2 = self.wikipedia_page.summary
                s1 = se2.find("\n")
                se2 = se2[s1: se2.find("\n", s1 + 1)]
                se2 = self.do_hide_words(self.wikipedia_page.title)
                if se2:
                    await ctx.send("妹「サマリーの二行目は\n「" + se2 + "\n」だよ！」")
                else:
                    await ctx.send("妹「サマリーの二行目はなかったよ！」")
        if key == 'pv':
            pv = self.get_pv()
            await ctx.send(f"妹「過去30日間の閲覧数は {pv} だよ！」")
        if key == 'category':
            await ctx.send(self.wikipedia_page.categories)
        if key == 'url':
            await ctx.send(self.wikipedia_page.url)

    def get_pv(self):
        encode_title = urllib.parse.quote(self.wikipedia_page.title)
        url = f'https://ja.wikipedia.org/w/index.php?title={encode_title}&action=info'
        page = requests.get(url)
        soup = bs4(page.content, 'lxml')
        pv_class = soup.find(class_='mw-pvi-month')
        return pv_class.string

    @quiz_wikipedia.command(aliases=['cl', 'create_list'])
    async def create_wordlist(self, ctx, target: str):
        await ctx.send("妹「単語帳を作るよ！」")
        await ctx.send("妹は懸命にペンを動かしている。")
        if target == 'wiki':
            self.wordlist = self.get_wikipedia_random_10words()
            await ctx.send("妹「単語帳を作成したよ！」")
        else:
            await ctx.send("妹「ごめんね、お兄ちゃん。上手く作れなかった…」")
            self.wordlist = []
            return

    def get_wikipedia_random_10words(self):
        """wikipediaからランダムで10個単語を選んだ単語帳を作成する"""
        words = [wikipedia.random() for _ in range(10)]
        return words

    @quiz_wikipedia.command(aliases=['add'])
    async def add_wordlist(self, ctx, target: str):
        """wordlistに単語を追加する。csv対応。"""
        words = target.split(",")
        self.wordlist.extend(words)
        await ctx.send(f"妹「単語帳に{len(words)}個の単語を書き加えたよ！」")

    @quiz_wikipedia.command(aliases=['gol', 'get_out_of_list'])
    async def get_wikipedia_page_for_wordlist(self, ctx):
        """作成した単語帳からランダムで単語を選び、その単語でwikipediaのページを取得する"""
        await ctx.send("妹「単語帳から適当に問題に出すね！」")
        if not self.wordlist:
            await ctx.send("妹「単語帳をまだ作ってないよ！お兄ちゃん！」")
            return
        random_word = self.wordlist.pop(random.randrange(len(self.wordlist)))
        try:
            self.wikipedia_page = wikipedia.page(random_word)
        except wikipedia.exceptions.DisambiguationError as e:
            await ctx.send("妹「あっ、書き損じしちゃってた…。」妹は消しゴムを取り出した。")
            self.wikipedia_page = None
            return
        await ctx.send("妹は問題を書きとめ、あなたからの質問に応える気が十分なようだ")

    @quiz_wikipedia.command(aliases=['wordlist'])
    async def show_wordlist(self, ctx):
        """wordlistを見る Discordの出力文字数限界が2000なので、2000未満の表示とする"""
        if not self.wordlist:
            await ctx.send("妹「単語帳に何も書いてないよ！お兄ちゃん！」")
            return
        print(", ".join(self.wordlist)[:1000])
        await ctx.send("\r\n".join(self.wordlist)[:1000])

    @quiz_wikipedia.command()
    async def delete_wordlist(self, ctx):
        self.wordlist = []
        await ctx.send("妹「新しい単語帳を用意したよ！」")

    @quiz_wikipedia.command(aliases=['prepare'])
    async def prepare_word_order_exercise_game(self, ctx):
        await self.create_wordlist(ctx, 'wiki')
        await self.show_wordlist(ctx)

    @quiz_wikipedia.command(aliases=['next'])
    async def next_word_order_exercise_game(self, ctx):
        await self.get_wikipedia_page_for_wordlist(ctx)
        if self.wikipedia_page:
            await self.print_hint(ctx, 'summary')
