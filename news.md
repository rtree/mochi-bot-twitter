---
layout: default
title: アーカイブ
permalink: /news/
---

# 📅 アーカイブ

過去のつぶやけなかったニュース

[🏠 ホーム]({{ site.baseurl }}/) | [フォローする](https://x.com/techandeco4242) | [📡 RSS]({{ site.baseurl }}/feed.xml)

---

{% for post in site.posts %}
- {{ post.date | date: "%Y-%m-%d" }} [{{ post.title }}]({{ post.url | relative_url }})
{% endfor %}
