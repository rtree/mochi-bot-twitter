# GitHub Pages用のニュースサイトセットアップ手順

## 1. 新しいGitHubリポジトリを作成

```bash
# リポジトリ名の例: mochi-news
# GitHub上で作成するか、以下のコマンドで作成
gh repo create mochi-news --public
```

## 2. 環境変数を設定

`.env`ファイルに以下を追加:

```
GITHUB_PAGES_REPO_PATH=./mochi-news
GITHUB_PAGES_REPO_URL=https://github.com/YOUR_USERNAME/mochi-news.git
```

## 3. リポジトリの初期セットアップ

```bash
cd mochi-news

# Jekyll設定ファイルを作成
cat > _config.yml << 'EOF'
title: もちおのニュースまとめ
description: テック・経済ニュースの日次まとめ
baseurl: ""
url: "https://YOUR_USERNAME.github.io/mochi-news"

# Build settings
markdown: kramdown
theme: minima

# RSS Feed
plugins:
  - jekyll-feed

# Feed settings
feed:
  path: feed.xml
EOF

# Gemfile作成
cat > Gemfile << 'EOF'
source "https://rubygems.org"

gem "github-pages", group: :jekyll_plugins
gem "jekyll-feed"
EOF

# index.md作成
cat > index.md << 'EOF'
---
layout: home
title: もちおのニュースまとめ
---

テック・経済ニュースの日次まとめだよ！ 🐱

RSSフィード: [feed.xml](/feed.xml)
EOF

# _postsディレクトリ作成
mkdir -p _posts

# コミット & プッシュ
git add .
git commit -m "Initial Jekyll setup"
git push -u origin main
```

## 4. GitHub Pagesを有効化

1. リポジトリのSettings → Pages
2. Source: "Deploy from a branch"
3. Branch: `main` / `/ (root)`
4. Save

## 5. 動作確認

```bash
# botを実行（GitHub Pages投稿あり）
python main.py nofetch nosummary

# GitHub Pages投稿なしで実行する場合
python main.py nopages
```

## 6. 公開URL

- サイト: `https://YOUR_USERNAME.github.io/mochi-news/`
- RSSフィード: `https://YOUR_USERNAME.github.io/mochi-news/feed.xml`

## コマンドラインオプション

| オプション | 説明 |
|-----------|------|
| `notweet` | Twitterへの投稿をスキップ |
| `nofetch` | ニュース取得をスキップ（ログから読み込み） |
| `nosummary` | 個別要約をスキップ |
| `nopages` | GitHub Pagesへの投稿をスキップ |
