---
layout: page
title: ニュースアーカイブ
permalink: /news/
---

# 📅 ニュースアーカイブ

<div class="twitter-follow">
  <a href="https://x.com/because2and2is4" target="_blank">🐦 X(Twitter)でフォロー</a>
</div>

---

{% for post in site.posts %}
<article class="post-item">
  <h2><a href="{{ post.url | prepend: site.baseurl }}">{{ post.title }}</a></h2>
  <time datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%Y年%m月%d日" }}</time>
</article>
{% endfor %}

---

📡 **RSSフィード**: [feed.xml]({{ site.baseurl }}/feed.xml)
