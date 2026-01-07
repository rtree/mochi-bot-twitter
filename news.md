---
layout: default
title: アーカイブ
permalink: /news/
---

# 📅 アーカイブ

過去のつぶやけなかったニュース

<div class="nav-links">
<a href="{{ site.baseurl }}/" class="nav-link-item">🏠 ホーム</a>
<a href="https://x.com/techandeco4242" class="nav-link-item" target="_blank">フォローする</a>
<a href="{{ site.baseurl }}/feed.xml" class="nav-link-item">📡 RSS</a>
</div>

---

{% for post in site.posts %}
<div class="post-list-item">
{{ post.date | date: "%Y-%m-%d" }} <a href="{{ post.url | relative_url }}" class="post-list-link">{{ post.title }}</a>
</div>
{% endfor %}
