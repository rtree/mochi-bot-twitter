---
layout: page
title: アーカイブ
permalink: /news/
---

<div class="profile-header">
  <div class="profile-name">📅 アーカイブ</div>
  <div class="profile-handle">過去のつぶやけなかったニュース</div>
</div>

<div class="home-links">
  <a href="https://x.com/techandeco4242" target="_blank" class="btn-follow">フォローする</a>
  <a href="{{ site.baseurl }}/feed.xml">📡 RSS</a>
</div>

{% for post in site.posts %}
<article class="post-item">
  <a href="{{ post.url | prepend: site.baseurl }}" style="text-decoration: none;">
    <div class="post-title">{{ post.title }}</div>
    <time datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%Y年%m月%d日" }}</time>
  </a>
</article>
{% endfor %}
