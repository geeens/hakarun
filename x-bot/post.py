#!/usr/bin/env python3
"""
ハカセ🦉 X自動投稿ボット

使い方:
  python3 post.py --draft 5    # ツール紹介の下書きを5件生成して保存
  python3 post.py --value 5    # 豆知識（ツール誘導なし）の下書きを5件生成して保存
  python3 post.py --list       # 保存済み下書きを一覧表示
  python3 post.py --send 3     # 下書き #3 をXに投稿
  python3 post.py --delete 3   # 下書き #3 を削除
  python3 post.py --auto       # ツール紹介か豆知識をランダムに生成して即投稿
"""

import os
import sys
import json
import random
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import anthropic
import tweepy

# ===== 初期設定 =====
load_dotenv()
SCRIPT_DIR = Path(__file__).parent
DRAFTS_FILE = SCRIPT_DIR / 'drafts.json'

# ===== ツール一覧 =====
TOOLS = [
    # お金・給与
    {'name': '手取り計算・比較', 'url': 'https://hakarun.net/money/tedori', 'cat': 'お金', 'hint': '年収500万の手取りは約390万円。給与アップ時の手取り差額も比較できる'},
    {'name': '残業代計算', 'url': 'https://hakarun.net/money/zangyo', 'cat': 'お金', 'hint': '残業代の割増率は通常25%。深夜・休日はさらに高くなる'},
    {'name': 'ボーナス手取り計算', 'url': 'https://hakarun.net/money/bonus', 'cat': 'お金', 'hint': '100万円のボーナスでも手取りは約80万円になることが多い'},
    {'name': '年収→月収・時給計算', 'url': 'https://hakarun.net/money/nenshu', 'cat': 'お金', 'hint': '年収400万円は月収約33万円、時給換算で約1,920円'},
    {'name': '社会保険料シミュレーション', 'url': 'https://hakarun.net/money/shakaihoken', 'cat': 'お金', 'hint': '社会保険料は給与の約14〜15%。会社も同額を負担している'},
    {'name': '退職金手取り計算', 'url': 'https://hakarun.net/money/taisyokukin', 'cat': 'お金', 'hint': '勤続20年超えると退職金の税控除が大きくなる'},
    {'name': '消費税計算', 'url': 'https://hakarun.net/money/shohizei', 'cat': 'お金', 'hint': '税込価格から税抜きを出すには÷1.1'},
    {'name': '割り勘計算', 'url': 'https://hakarun.net/money/warikan', 'cat': 'お金', 'hint': '人数と合計金額を入れるだけで一人分をすぐ計算'},
    {'name': '住民税計算', 'url': 'https://hakarun.net/money/juuminzei', 'cat': 'お金', 'hint': '住民税は前年の所得に対してかかる。退職後に一括請求されることも'},
    {'name': '手取りから額面逆算', 'url': 'https://hakarun.net/money/gyaku', 'cat': 'お金', 'hint': '手取り30万円が欲しいなら額面は約39万円必要'},
    {'name': '副業収入の税金計算', 'url': 'https://hakarun.net/money/fukugyo', 'cat': 'お金', 'hint': '副業収入が年20万円を超えると確定申告が必要'},
    {'name': '育児休業給付金計算', 'url': 'https://hakarun.net/money/ikukyu', 'cat': 'お金', 'hint': '育休中は最初の180日間は給与の67%が支給される'},
    {'name': '傷病手当金計算', 'url': 'https://hakarun.net/money/shobyo', 'cat': 'お金', 'hint': '病気で休んでも給与の約2/3が最大1年半もらえる'},
    {'name': '雇用保険・失業給付計算', 'url': 'https://hakarun.net/money/koyo', 'cat': 'お金', 'hint': '失業手当は離職前6ヶ月の平均給与の50〜80%'},
    {'name': '年金受給額シミュレーション', 'url': 'https://hakarun.net/money/nenkin', 'cat': 'お金', 'hint': '平均年収400万円で40年加入すると老齢厚生年金は月約10万円'},
    # 健康・医療
    {'name': 'BMI計算', 'url': 'https://hakarun.net/health/bmi', 'cat': '健康', 'hint': 'BMI22が最も病気になりにくい標準体重。25以上が肥満の目安'},
    {'name': '基礎代謝計算', 'url': 'https://hakarun.net/health/metabolism', 'cat': '健康', 'hint': '基礎代謝は30代から年1%ずつ低下する'},
    {'name': '消費カロリー計算', 'url': 'https://hakarun.net/health/calorie', 'cat': '健康', 'hint': '1kgの脂肪を落とすには約7,200kcalの消費が必要'},
    {'name': '体脂肪率計算', 'url': 'https://hakarun.net/health/taishibo', 'cat': '健康', 'hint': '男性の標準体脂肪率は10〜20%、女性は20〜30%'},
    {'name': '睡眠時間計算', 'url': 'https://hakarun.net/health/suimin', 'cat': '健康', 'hint': '睡眠は90分サイクル。6時間・7.5時間で起きると目覚めやすい'},
    {'name': '水分補給量計算', 'url': 'https://hakarun.net/health/suibun', 'cat': '健康', 'hint': '1日に必要な水分量は体重×35ml。体重60kgなら約2.1リットル'},
    {'name': 'アルコール分解時間計算', 'url': 'https://hakarun.net/health/alctime', 'cat': '健康', 'hint': 'ビール500mlが抜けるのに約3〜4時間かかる'},
    {'name': 'ストレス度チェック', 'url': 'https://hakarun.net/health/stress', 'cat': '健康', 'hint': 'ストレスは数値化できる。ライフイベントの積み重ねで健康リスクがわかる'},
    # 暮らし・節約
    {'name': 'ローン返済シミュレーション', 'url': 'https://hakarun.net/life/loan', 'cat': '暮らし', 'hint': '3000万を35年・金利1%で借りると総返済額は約3550万円'},
    {'name': '電気代計算', 'url': 'https://hakarun.net/life/denki', 'cat': '暮らし', 'hint': 'エアコン1台を1日8時間使うと月約6,500円かかる'},
    {'name': 'ガソリン代計算', 'url': 'https://hakarun.net/life/gasoline', 'cat': '暮らし', 'hint': '燃費10km/Lの車で月1,000km走るとガソリン代は約17,000円'},
    {'name': '積立貯金シミュレーション', 'url': 'https://hakarun.net/life/chochiku', 'cat': '暮らし', 'hint': '毎月3万円を20年積み立てると元本720万円になる'},
    {'name': 'スマホ代節約計算', 'url': 'https://hakarun.net/life/sumaho', 'cat': '暮らし', 'hint': '大手から格安SIMに変えると年間6〜12万円節約できることも'},
    {'name': '車の維持費計算', 'url': 'https://hakarun.net/life/kuruma', 'cat': '暮らし', 'hint': '普通車の年間維持費は平均約40〜50万円。月3〜4万円かかる'},
    {'name': '旅行費用計算', 'url': 'https://hakarun.net/life/travel', 'cat': '暮らし', 'hint': '人数・泊数・交通費を入れると旅行の合計費用がすぐわかる'},
    {'name': '出産・育児費用計算', 'url': 'https://hakarun.net/life/baby', 'cat': '暮らし', 'hint': '出産から3歳までにかかる費用は平均200〜300万円'},
    # 節税
    {'name': 'ふるさと納税 上限額・あといくら計算', 'url': 'https://hakarun.net/tax/furusato', 'cat': '節税', 'hint': '年収500万・独身なら上限は約6万円。返礼品ももらえてお得'},
    {'name': '医療費控除・還付金計算', 'url': 'https://hakarun.net/tax/iryouhi', 'cat': '節税', 'hint': '年間医療費が10万円を超えると確定申告で還付が受けられる'},
    {'name': '高額療養費計算', 'url': 'https://hakarun.net/health/kougaku', 'cat': '節税', 'hint': '月の医療費が一定額を超えると払い戻しがある'},
    {'name': '住宅ローン控除・還付金計算', 'url': 'https://hakarun.net/tax/jutaku', 'cat': '節税', 'hint': 'ローン残高の0.7%が毎年所得税から控除される。最大13年間'},
    {'name': 'iDeCo節税計算', 'url': 'https://hakarun.net/tax/ideco', 'cat': '節税', 'hint': 'iDeCoで月2万円積み立てると年間約4.8万円節税できる（年収500万の場合）'},
    {'name': '贈与税計算', 'url': 'https://hakarun.net/tax/gift', 'cat': '節税', 'hint': '年間110万円以内の贈与なら贈与税がかからない'},
    # 計算・変換
    {'name': 'パーセント計算', 'url': 'https://hakarun.net/calc/percent', 'cat': '計算', 'hint': '30%オフの金額や消費税込みの計算をかんたんに'},
    {'name': '外貨換算', 'url': 'https://hakarun.net/calc/gaika', 'cat': '計算', 'hint': '海外旅行前に円→ドル・ユーロをかんたん計算'},
    {'name': '偏差値計算', 'url': 'https://hakarun.net/calc/hensachi', 'cat': '計算', 'hint': '点数・平均点・標準偏差を入れると偏差値がすぐわかる'},
    {'name': '面積計算', 'url': 'https://hakarun.net/calc/menseki', 'cat': '計算', 'hint': '縦×横の面積を㎡・帖・坪に一括変換'},
    # 投資・資産
    {'name': '複利計算', 'url': 'https://hakarun.net/invest/fukuri', 'cat': '投資', 'hint': '100万円を年利5%で20年運用すると約265万円に。複利の力はすごい'},
    {'name': 'NISA枠・積立シミュレーション', 'url': 'https://hakarun.net/invest/nisa', 'cat': '投資', 'hint': '月5万円を年利5%で20年積み立てると約2,055万円になることも'},
    {'name': '損益計算', 'url': 'https://hakarun.net/invest/soneki', 'cat': '投資', 'hint': '株の購入価格と売却価格から損益額・損益率を計算'},
    {'name': '不動産利回り計算', 'url': 'https://hakarun.net/invest/rimawari', 'cat': '投資', 'hint': '表面利回りと実質利回りは全然違う。空室率・諸経費込みで計算しよう'},
    {'name': '老後資金計算', 'url': 'https://hakarun.net/invest/rogo', 'cat': '投資', 'hint': '老後30年で月25万円必要なら9,000万円。年金を引いた不足分を計算しよう'},
    {'name': '生命保険必要額計算', 'url': 'https://hakarun.net/invest/seimei', 'cat': '投資', 'hint': '必要な保険金額は家族構成・年収・ローン残高によって大きく変わる'},
]

# ===== 豆知識テーマ一覧（ツール誘導なし・暮らしや投資に役立つ話）=====
VALUE_TOPICS = [
    {'name': '複利の力', 'cat': '投資', 'hint': '毎月3万円を年利5%で30年積み立てると元本1,080万円が約2,500万円に。増えた分のほとんどは複利（利益にも利益がつく仕組み）'},
    {'name': '72の法則', 'cat': '投資', 'hint': '72÷年利＝お金が2倍になる年数。年利5%なら約14年、年利7%なら約10年で2倍'},
    {'name': '固定費の見直し', 'cat': '節約', 'hint': '月1万円の固定費を削ると年12万円。年利5%で20年運用すれば約411万円の差になる。一度見直せば自動で効き続ける'},
    {'name': '生活防衛資金', 'cat': '投資', 'hint': '投資の前にまず現金を確保。目安は会社員で生活費の3〜6ヶ月分、自営業で6〜12ヶ月分。暴落時の狼狽売りを防げる'},
    {'name': 'ドルコスト平均法', 'cat': '投資', 'hint': '毎月決まった額を買うと、高い時は少なく・安い時は多く買える。タイミングを読まなくていいので初心者ほど積立が向く'},
    {'name': '手取りの実際', 'cat': 'お金', 'hint': '年収500万でも手取りは約390万円（月約32万）。社会保険料・所得税・住民税で約110万円が引かれる'},
    {'name': '先取り貯金', 'cat': '節約', 'hint': '「残ったら貯金」ではなく「先に貯金してから残りで生活」。給料日に自動で別口座へ移すのがコツ'},
    {'name': 'インフレと現金', 'cat': 'お金', 'hint': 'メガバンクの普通預金金利は2026年に過去最高水準の0.4%。それでもインフレ率（約2〜3%）には負けるので、現金だけでは価値が目減りする'},
    {'name': '4%ルール', 'cat': '投資', 'hint': '年間生活費の25倍を貯めて年4%ずつ取り崩せば資産が長持ちする考え方。月20万生活なら必要額は約6,000万円'},
    {'name': '早く始める価値', 'cat': '投資', 'hint': '月3万を年利5%で積立、25歳開始は65歳で約4,579万円、35歳開始は約2,497万円。たった10年で約2,000万円の差'},
    {'name': '平均と中央値', 'cat': 'お金', 'hint': '20代の貯金「平均」は約180万だが「中央値（ど真ん中）」は約80万。平均は一部のお金持ちに引き上げられるので中央値で見るのが正解'},
    {'name': '最初の100万円が一番大変', 'cat': '投資', 'hint': '序盤は複利がほぼ効かず自分の入金力だけで増やす世界。100万の年5%は年5万だが、1000万の年5%は年50万。最初の壁を越えると加速する'},
    {'name': 'ふるさと納税の仕組み', 'cat': '節税', 'hint': '実質2,000円の負担で各地の特産品がもらえる制度。年収450万・独身なら上限の目安は約5万円。税金の使い道を自分で選べる'},
    {'name': 'iDeCoの節税', 'cat': '節税', 'hint': '掛金が全額所得控除になる。年収500万の人が月2万円積み立てると年間約4.8万円の節税。ただし60歳まで引き出せない'},
    {'name': 'ボーナスの手取り', 'cat': 'お金', 'hint': '額面100万円のボーナスでも社会保険料と所得税で約20万円引かれ、手取りは約80万円になることが多い'},
]

SYSTEM_PROMPT = """あなたはフクロウ博士「ハカセ」として、X（旧Twitter）に投稿する日本語のツイートを作成します。

【キャラクター設定】
- 🦉 なんでも計算できる知識豊富なフクロウ博士
- 親しみやすく、難しいことをわかりやすく解説するのが得意
- 語尾は「〜だよ」「〜なんだ」「〜してみよう」などカジュアルかつ知的なトーン

【ツイートのルール】
- 必ず「🦉ハカセの豆知識」で書き始める
- URL・ハッシュタグを除いて140文字以内
- 具体的な数字を必ず1つ以上含める
- 改行を使って読みやすくする
- 関連するハッシュタグを2〜3個つける（例：#手取り #お金の知識）
- 最後にツールのURLを入れる
- ツイート本文のみ出力する（前置きや説明文は不要）"""


VALUE_SYSTEM_PROMPT = """あなたはフクロウ博士「ハカセ」として、X（旧Twitter）に投稿する暮らしや投資に役立つ日本語の豆知識ツイートを作成します。

【キャラクター設定】
- 🦉 なんでも計算できる知識豊富なフクロウ博士
- 親しみやすく、難しいことをわかりやすく解説するのが得意
- 語尾は「〜だよ」「〜なんだ」「〜してみよう」などカジュアルかつ知的なトーン

【ツイートのルール】
- 必ず「🦉ハカセの豆知識」で書き始める
- ハッシュタグを除いて140文字以内
- 具体的な数字を必ず1つ以上含める
- 改行を使って読みやすくする
- 読んだだけで「へぇ！」「やってみよう」と思える、それ単体で完結した内容にする
- URL・ツール名・サイト名は一切入れない（宣伝しない）
- 関連するハッシュタグを2〜3個つける（例：#お金の知識 #投資 #NISA）
- ツイート本文のみ出力する（前置きや説明文は不要）"""


def load_drafts():
    """下書きファイルを読み込む"""
    if not DRAFTS_FILE.exists():
        return {"drafts": [], "next_id": 1}
    with open(DRAFTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_drafts_file(data):
    """下書きファイルを保存する"""
    with open(DRAFTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def make_tweet(client, kind):
    """Claude で1件分のツイート本文を生成する。
    kind='tool' ならツール紹介、kind='value' なら豆知識（URLなし）。
    戻り値: (本文, ネタの名前, カテゴリ)"""
    if kind == 'value':
        topic = random.choice(VALUE_TOPICS)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=VALUE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"""以下のテーマで、暮らしや投資に役立つ豆知識ツイートを1つ作成してください。

テーマ：{topic['name']}
カテゴリ：{topic['cat']}
参考になる数字・情報：{topic['hint']}"""
            }]
        )
        return response.content[0].text.strip(), topic['name'], topic['cat']

    tool = random.choice(TOOLS)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""以下のツールを紹介するツイートを1つ作成してください。

ツール名：{tool['name']}
カテゴリ：{tool['cat']}
URL：{tool['url']}
参考になる数字・情報：{tool['hint']}"""
        }]
    )
    return response.content[0].text.strip(), tool['name'], tool['cat']


def generate_drafts(count, kind='tool'):
    """Claude を使って下書きを生成する（kind='tool' or 'value'）"""
    if not os.environ.get('CLAUDE_API_KEY'):
        print("❌ CLAUDE_API_KEY が設定されていません。.env ファイルを確認してください。")
        sys.exit(1)

    label = '豆知識' if kind == 'value' else 'ツール紹介'
    client = anthropic.Anthropic(api_key=os.environ['CLAUDE_API_KEY'])
    data = load_drafts()
    new_drafts = []

    print(f"✍️  {label}の下書きを {count}件 生成中...\n")

    for i in range(count):
        tweet_text, name, cat = make_tweet(client, kind)
        print(f"  [{i+1}/{count}] 「{name}」の投稿を生成中...")

        draft = {
            "id": data["next_id"],
            "tool": name,
            "category": cat,
            "kind": kind,
            "text": tweet_text,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "posted": False
        }
        data["drafts"].append(draft)
        data["next_id"] += 1
        new_drafts.append(draft)

    save_drafts_file(data)
    print(f"\n✅ {count}件の下書きを保存しました。\n")
    print("── 生成された下書き ──")
    for d in new_drafts:
        print(f"\n📝 下書き #{d['id']}（{d['tool']}）")
        print("─" * 40)
        print(d['text'])
        print("─" * 40)
    print(f"\n投稿するには: python3 post.py --send [番号]")


def list_drafts():
    """保存済み下書きを一覧表示する"""
    data = load_drafts()
    pending = [d for d in data["drafts"] if not d["posted"]]

    if not pending:
        print("📭 未投稿の下書きはありません。")
        print("   下書きを生成するには: python3 post.py --draft 5")
        return

    print(f"📋 未投稿の下書き（{len(pending)}件）\n")
    for d in pending:
        print(f"── 下書き #{d['id']}（{d['category']}：{d['tool']}）{d['created_at']}")
        print(d['text'])
        print("─" * 45)
        print()
    print(f"投稿するには: python3 post.py --send [番号]")


def send_tweet(draft_id):
    """指定した下書きをXに投稿する"""
    for key in ['X_API_KEY', 'X_API_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET']:
        if not os.environ.get(key):
            print(f"❌ {key} が設定されていません。.env ファイルを確認してください。")
            sys.exit(1)

    data = load_drafts()
    draft = next((d for d in data["drafts"] if d["id"] == draft_id and not d["posted"]), None)

    if not draft:
        print(f"❌ 下書き #{draft_id} が見つかりません（または投稿済みです）。")
        print("   一覧を確認するには: python3 post.py --list")
        return

    print(f"📤 以下の内容をXに投稿します：\n")
    print("─" * 45)
    print(draft['text'])
    print("─" * 45)
    confirm = input("\nこの内容で投稿しますか？ (y/n): ").strip().lower()

    if confirm != 'y':
        print("❌ 投稿をキャンセルしました。")
        return

    client = tweepy.Client(
        consumer_key=os.environ['X_API_KEY'],
        consumer_secret=os.environ['X_API_SECRET'],
        access_token=os.environ['X_ACCESS_TOKEN'],
        access_token_secret=os.environ['X_ACCESS_TOKEN_SECRET']
    )

    try:
        response = client.create_tweet(text=draft['text'])
        tweet_id = response.data['id']
        draft['posted'] = True
        draft['posted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        draft['tweet_id'] = tweet_id
        save_drafts_file(data)
        print(f"\n✅ 投稿しました！")
        print(f"   https://x.com/hakase_hakarun/status/{tweet_id}")
    except Exception as e:
        print(f"❌ 投稿に失敗しました: {e}")


def delete_draft(draft_id):
    """指定した下書きを削除する"""
    data = load_drafts()
    before = len(data["drafts"])
    data["drafts"] = [d for d in data["drafts"] if not (d["id"] == draft_id and not d["posted"])]

    if len(data["drafts"]) == before:
        print(f"❌ 下書き #{draft_id} が見つかりません。")
        return

    save_drafts_file(data)
    print(f"🗑️  下書き #{draft_id} を削除しました。")


def clear_drafts():
    """未投稿の下書きをすべて削除する"""
    data = load_drafts()
    pending = [d for d in data["drafts"] if not d["posted"]]

    if not pending:
        print("📭 削除する未投稿の下書きはありません。")
        return

    confirm = input(f"未投稿の下書き {len(pending)}件 をすべて削除しますか？ (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ キャンセルしました。")
        return

    data["drafts"] = [d for d in data["drafts"] if d["posted"]]
    save_drafts_file(data)
    print(f"🗑️  {len(pending)}件の下書きを削除しました。")


def auto_post():
    """ツイートを自動生成して即投稿する（確認なし）"""
    for key in ['CLAUDE_API_KEY', 'X_API_KEY', 'X_API_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET']:
        if not os.environ.get(key):
            print(f"❌ {key} が設定されていません。")
            sys.exit(1)

    # Claude でツイート生成（ツール紹介と豆知識をランダムに選ぶ）
    claude_client = anthropic.Anthropic(api_key=os.environ['CLAUDE_API_KEY'])
    kind = random.choice(['tool', 'value'])
    tweet_text, name, cat = make_tweet(claude_client, kind)
    label = '豆知識' if kind == 'value' else 'ツール紹介'
    print(f"✍️  {label}「{name}」の投稿を生成中...")

    # X に投稿
    twitter_client = tweepy.Client(
        consumer_key=os.environ['X_API_KEY'],
        consumer_secret=os.environ['X_API_SECRET'],
        access_token=os.environ['X_ACCESS_TOKEN'],
        access_token_secret=os.environ['X_ACCESS_TOKEN_SECRET']
    )

    try:
        result = twitter_client.create_tweet(text=tweet_text)
        tweet_id = result.data['id']

        # 投稿履歴を保存
        data = load_drafts()
        data["drafts"].append({
            "id": data["next_id"],
            "tool": name,
            "category": cat,
            "kind": kind,
            "text": tweet_text,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "posted": True,
            "posted_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "tweet_id": tweet_id
        })
        data["next_id"] += 1
        save_drafts_file(data)

        print(f"✅ 自動投稿しました！")
        print(f"   {tweet_text[:50]}...")
        print(f"   https://x.com/hakase_hakarun/status/{tweet_id}")
    except Exception as e:
        print(f"❌ 投稿に失敗しました: {e}")
        sys.exit(1)


# ===== メイン処理 =====
def main():
    parser = argparse.ArgumentParser(description='ハカセ🦉 X自動投稿ボット')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--draft', type=int, metavar='件数', help='ツール紹介の下書きを生成する（例: --draft 5）')
    group.add_argument('--value', type=int, metavar='件数', help='豆知識（ツール誘導なし）の下書きを生成する（例: --value 5）')
    group.add_argument('--list', action='store_true', help='下書き一覧を表示する')
    group.add_argument('--send', type=int, metavar='番号', help='指定した下書きをXに投稿する（例: --send 3）')
    group.add_argument('--delete', type=int, metavar='番号', help='指定した下書きを削除する（例: --delete 3）')
    group.add_argument('--auto', action='store_true', help='自動生成して即投稿する（確認なし）')
    group.add_argument('--clear', action='store_true', help='未投稿の下書きをすべて削除する')
    args = parser.parse_args()

    if args.draft:
        generate_drafts(args.draft, kind='tool')
    elif args.value:
        generate_drafts(args.value, kind='value')
    elif args.list:
        list_drafts()
    elif args.send:
        send_tweet(args.send)
    elif args.delete:
        delete_draft(args.delete)
    elif args.auto:
        auto_post()
    elif args.clear:
        clear_drafts()


if __name__ == '__main__':
    main()
