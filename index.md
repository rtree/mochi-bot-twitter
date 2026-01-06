---
layout: default
title: テクの猫
---

# 🐱 テクの猫

**@techandeco4242 のつぶやけなかったニュース**

Xでは文字数制限で載せきれなかったテック・経済ニュースをこちらでまとめてるよ。毎日更新中！

[📅 アーカイブ]({{ site.baseurl }}/news/) | [フォローする](https://x.com/techandeco4242) | [📡 RSS]({{ site.baseurl }}/feed.xml)

---

## 最新の投稿

{% for post in site.posts limit:5 %}
- {{ post.date | date: "%Y-%m-%d" }} [{{ post.title }}]({{ post.url | relative_url }})
{% endfor %}

[📅 すべての投稿を見る →]({{ site.baseurl }}/news/)

