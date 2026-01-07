---
layout: default
title: テクの猫
---

# 🐱 テクの猫

**@techandeco4242 のつぶやけなかったニュース**

Xでは文字数制限で載せきれなかったテック・経済ニュースをこちらでまとめてるよ。毎日更新中！

<div class="nav-links">
<a href="{{ site.baseurl }}/news/" class="nav-link-item">📅 アーカイブ</a>
<a href="https://x.com/techandeco4242" class="nav-link-item" target="_blank">フォローする</a>
<a href="{{ site.baseurl }}/feed.xml" class="nav-link-item">📡 RSS</a>
</div>

---

## 最新の投稿

{% for post in site.posts limit:5 %}
<div class="post-list-item">
{{ post.date | date: "%Y-%m-%d" }} <a href="{{ post.url | relative_url }}" class="post-list-link">{{ post.title }}</a>
</div>
{% endfor %}

<div class="view-all">
<a href="{{ site.baseurl }}/news/" class="view-all-link">📅 すべての投稿を見る →</a>
</div>

