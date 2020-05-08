from seminars import db
from seminars.toggle import toggle, toggle3way
from flask import request
from collections import defaultdict


class WebTopic(object):
    # A topic has an identifier, a name for displaying and a list of children
    def __init__(self, id, name):
        self.id = id
        self.name = name
        # the following are filled in by TopicDAG __init__
        self.children = []
        self.parents = []

    @property
    def ancestors(self):
        if not self.parents:
            return []
        else:
            return sorted(set([elt.id for elt in self.parents] + sum([elt.ancestors for elt in self.parents], [])))


class TopicDAG(object):
    def __init__(self):
        self.by_id = {}

        def sort_key(x):
            return x.name.lower()

        for rec in db.new_topics.search():
            self.by_id[rec["topic_id"]] = topic = WebTopic(rec["topic_id"], rec["name"])
            topic.children = rec["children"]
        for topic in self.by_id.values():
            for cid in topic.children:
                self.by_id[cid].parents.append(topic)
        for topic in self.by_id.values():
            topic.children = [self.by_id[cid] for cid in topic.children]
            topic.children.sort(key=sort_key)
            topic.parents.sort(key=sort_key)
        self.subjects = sorted(
            (topic for topic in self.by_id.values() if not topic.parents), key=sort_key
        )

    def read_cookie(self, manage=None):
        if manage is not None:
            # manage is a talk or seminar
            return {topic: 1 for topic in manage.topics}
        res = defaultdict(int)
        if request.cookies.get("topics", ""):
            # old key
            for elt in request.cookies.get("topics", "").split(","):
                if '_' in elt:
                    sub, top = elt.split("_", 1)
                    if sub in self.by_id:
                        res[sub] = 1
                    if elt in self.by_id:
                        res[elt] = 1  # full topic
            # FIXME we need to trigger deletion of the cookie  when building the response
            # and setting the new topics_dict cookie
        for elt in request.cookies.get("topics_dict", "").split(","):
            if ':' in elt:
                key, val = elt.split(":", 1)
                try:
                    val = int(val)
                    if val in [0, 1, 2] and key in self.by_id:
                        res[key] = int(elt)
                except ValueError:
                    pass
        res[None] = 1 if request.cookies.get('filter_topic', '0') != '0' else 0
        return res

    def _link(self, parent_id="root", topic_id=None, counts={}, manage=None):
        if topic_id is None:
            tid = name = "topic"
            onclick = "toggleFilterView(this.id)"
            count = ""
        else:
            tid = topic_id
            topic = self.by_id[tid]
            name = topic.name
            count = counts.get(topic_id, 0)
            count = (" (%s)" % count) if count else ""
            if not topic.children:
                return name + count
            if manage is None:
                onclick = "toggleTopicView('%s', '%s')" % (parent_id, tid)
            else:
                onclick = "manageTopicView('%s', '%s')" % (parent_id, tid)
        return '<a id="{0}-filter-btn" class="likeknowl {1}-tlink" onclick="{2}; return false;">{3}</a>{4}'.format(
            tid, parent_id, onclick, name, count
        )

    def _toggle(self, parent_id="root", topic_id=None, cookie=None, manage=None):
        if cookie is None:
            cookie = self.read_cookie(manage=manage)
        kwds = {}
        if topic_id is None:
            tid = "topic"
            tclass = toggle
            onchange = "toggleFilters(this.id);"
        else:
            tid = parent_id + "--" + topic_id
            topic = self.by_id[topic_id]
            if topic.children and manage is None:
                tclass = toggle3way
            else:
                tclass = toggle
            if manage is None:
                onchange = "toggleTopicDAG(this.id);"
            else:
                onchange = "manageTopicDAG(this.id);"
            kwds["classes"] = " ".join([topic_id] + ["sub_" + elt for elt in topic.ancestors])

        return tclass(tid, value=cookie[topic_id], onchange=onchange, **kwds)

    def filter_link(self, parent_id="root", topic_id=None, counts={}, cookie=None, manage=None):
        padding = ' style="padding-right: 2em;"' if topic_id is None else ''
        return "<td>%s</td><td%s>%s</td>" % (
            self._toggle(parent_id, topic_id, cookie, manage),
            padding,
            self._link(parent_id, topic_id, counts, manage),
        )

    def link_pair(self, parent_id="root", topic_id=None, counts={}, cols=1, cookie=None, manage=None):
        return """
<div class="toggle_pair col{0}">
  <table><tr>{1}</tr></table>
</div>""".format(
            cols, self.filter_link(parent_id, topic_id, counts, cookie=cookie, manage=manage)
        )

    def filter_pane(self, parent_id="root", topic_id=None, counts={}, cookie=None, manage=None):
        if cookie is None:
            cookie = self.read_cookie(manage=manage)
        if topic_id is None:
            tid = "topic"
            topics = self.subjects
        else:
            tid = topic_id
            topics = self.by_id[tid].children
        childpanes = [topic.id for topic in topics if topic.children]
        mlen = max(len(topic.name) for topic in topics)
        # The following are guesses that haven't been tuned.
        if mlen > 50:
            cols = 1
        elif mlen > 35:
            cols = 2
        elif mlen > 25:
            cols = 3
        elif mlen > 16:
            cols = 4
        elif mlen > 10:
            cols = 5
        else:
            cols = 6
        return """
<div id="{0}-{1}-pane" class="filter-menu {0}-subpane" style="display:none;">
{2}
{3}
</div>""".format(
            parent_id,
            tid,
            "\n".join(self.link_pair(tid, topic.id, counts, cols, cookie, manage) for topic in topics),
            "\n".join(self.filter_pane(tid, child, counts, cookie, manage) for child in childpanes),
        )


topic_dag = TopicDAG()
