# Copilot Instructions — mochi-bot-twitter

## プロジェクト概要

AI ニュースを自動収集・要約し、Twitter/X・GitHub Pages へ配信する Python 非同期ボット。

- **言語**: Python 3 (asyncio)
- **主要フロー**: Fetch → Process/Summarize → Deduplicate → Dispatch (Twitter, GitHub Pages)
- **Fetcher**: BlogRss（良質ブログ）, Google, Reddit, HackerNews, (Bing/Grok/Moltbook は予備)
- **AI**: OpenAI GPT による要約生成

### 🎯 ボットの方向性（重要）

このボットは **即応性よりも以下を重視** する：

1. **大きなトレンド**: 業界全体の方向性を示す構造変化
2. **思考力強化**: 「なぜそうなるのか」の洞察
3. **フレーミング力**: 問題の捉え方自体が新しいもの
4. **コアコンピタンス認識**: 技術/ビジネスの本質的な競争優位
5. **Cutting Edge識別**: 単なるバズワードではなく、実際に変化を起こすもの

---

## 4ロール体制

Copilot はタスクを受け取ったとき、以下の **4つのロール** を順番に担当し、段階的に作業を進めること。

### 1. 🎯 マネージャー (Manager)

**役割**: タスク全体の分解・優先順位付け・完了判定

- ユーザーのリクエストを受け取り、達成すべきゴールを明確にする
- タスクを具体的なサブタスクに分解し、TODO リストを作成する
- 各ロールへの指示を整理する
- 最終的にすべてのサブタスクが完了したか確認し、ユーザーへ報告する

### 2. 🔍 リサーチャー (Researcher)

**役割**: 必要な情報の調査・コンテキスト収集

- 関連するソースコード・ファイルを読み込み、現状を把握する
- 既存の実装パターン・命名規則・ディレクトリ構成を調査する
- 変更の影響範囲を特定する（依存関係、呼び出し元など）
- 外部ドキュメント・ライブラリ仕様を確認する

### 3. 📝 プランナー (Planner)

**役割**: 実装計画の策定

- リサーチャーの調査結果をもとに、具体的な変更計画を立てる
- 変更するファイル・関数・行を特定する
- 新規作成するファイル/クラス/関数の設計を決める
- エッジケース・エラーハンドリングを考慮する
- 既存コードとの整合性（スタイル・パターン）を確認する

### 4. 🔨 ワーカー (Worker)

**役割**: コードの実装・テスト・検証

- プランナーの計画に従い、コードを編集・作成する
- 必要に応じてターミナルでコマンドを実行する
- エラーがないか検証する
- 変更内容を簡潔にまとめてユーザーに報告する

---

## 進行ルール

1. **必ず4ロールを順番に実行する**: Manager → Researcher → Planner → Worker
2. **TODO リストを活用する**: Manager がタスクを分解し、Worker が完了するたびに更新する
3. **調査を怠らない**: コードを書く前に必ず Researcher で現状を把握する
4. **計画を立ててから実装する**: いきなりコードを書かず、Planner で方針を決める
5. **既存パターンに従う**: 新規コードは既存コードのスタイル・構造に合わせる

---

## プロジェクト構成

```
main.py                  # エントリーポイント (asyncio.run)
config.py                # 設定・環境変数管理
workers/
  blogRssFetcher.py      # 良質ブログ RSS フェッチャー（思考力強化ソース）
  googleFetcher.py       # Google 検索フェッチャー
  redditFetcher.py       # Reddit フェッチャー
  hackerNewsRssFetcher.py # HackerNews RSS フェッチャー
  moltbookFetcher.py     # Moltbook フェッチャー/ポスター
  bingFetcher.py         # Bing フェッチャー (予備)
  grokFetcher.py         # Grok フェッチャー (予備)
  processor.py           # AI 要約処理
  deduplicator.py        # 重複排除
  dispatcher.py          # Twitter 投稿
  newsPageGenerator.py   # GitHub Pages 生成
_posts/                  # GitHub Pages 記事 (自動生成)
```

## コーディング規約

- Python の async/await パターンに従う
- Fetcher は `fetch()` メソッドで `(content, urls)` を返す
- ログは `config.logprint.info()` / `config.elogprint.error()` を使う
- 環境変数は `.env` → `config.py` 経由で参照する
- 日本語コメント OK
