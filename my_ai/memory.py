from __future__ import annotations
from .db import execute, search_knowledge
def remember(topic,title,content,source_url=None):
    return execute("INSERT INTO knowledge(topic,title,content,source_url) VALUES(?,?,?,?)",(topic,title,content,source_url))
def recall(query,limit=8): return search_knowledge(query,max(1,min(limit,50)))
