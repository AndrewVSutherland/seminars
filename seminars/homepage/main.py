from seminars.app import app
from seminars import db
from seminars.talk import WebTalk, talks_search, talks_lucky
from seminars.seminar import seminars_lucky
from seminars.utils import topics, toggle
from seminars.institution import institutions, WebInstitution
from flask import render_template, request, url_for
from seminars.seminar import seminars_search
from flask_login import current_user
import datetime
import pytz
from collections import Counter
from lmfdb.utils.search_parsing import search_parser
from dateutil.parser import parse

from lmfdb.utils import (
    SearchArray,
    TextBox,
    SelectBox,
    CheckBox,
    to_dict,
    search_wrap,
    flash_error,
)


def get_now():
    # Returns now in UTC, comparable to time-zone aware datetimes from the database
    return datetime.datetime.now(pytz.UTC)


def parse_topic(info, query, prefix):
    # of the talk
    topic = info.get(prefix + "_topic")
    if topic:
        query["topics"] = {"$contains": topic}


def parse_institution_sem(info, query, prefix="seminar"):
    inst = info.get(prefix + "_institution")
    if inst == "None":
        query["institutions"] = None
    elif inst:
        # one day we will do joins
        query["institutions"] = {"$contains": inst}


def parse_institution_talk(info, query, prefix="talk"):
    if info.get("institution"):
        sub_query = {}
        # one day we will do joins
        parse_institution_sem(info, sub_query, prefix="talk")
        sem_shortnames = list(seminars_search(sub_query, "shortname"))
        query["seminar_id"] = {"$in": sem_shortnames}


def parse_online(info, query, prefix):
    if info.get(prefix + "_online") == "yes":
        query["online"] = True

def parse_offline(info, query, prefix):
    if info.get(prefix + "_offline") == "yes":
        query["room"] = {"$exists": True}

def parse_substring(info, query, field, qfields, start="%", end="%"):
    if info.get(field):
        kwds = [elt.strip() for elt in info.get(field).split(",") if elt.strip()]
        for qfield in qfields:
            query[qfield] = {"$or": [{"$like": start + elt + end} for elt in kwds]}


def parse_access(info, query, prefix):
    # we want exact matches
    access = info.get(prefix + "_access")
    if access == "open":
        query["access"] = "open"
    elif access == "users":
        query["access"] = {"$or": ["open", "users"]}

def parse_date(info, query):
    tz = current_user.tz
    date = info.get("daterange")
    if date:
        sub_query = {}
        if "-" not in date:
            # make it into a range
            date = date + "-" + date
        start, end = date.split("-")
        if start.strip():
            try:
                start = tz.localize(parse(start))
            except Exception:
                flash_error("Could not parse date: %s", start)
            sub_query["$gte"] = start
        if end.strip():
            try:
                end = tz.localize(parse(end))
            except Exception:
                flash_error("Could not parse date: %s", end)
            end = end + datetime.timedelta(hours=23, minutes=59, seconds=59)
            sub_query["$lte"] = end
        if sub_query:
            query["start_time"] = sub_query


def parse_video(info, query):
    v = info.get("video")
    if v == "yes":
        query["video_link"] = {"$not": None}

def talks_parser(info, query):
    parse_topic(info, query, prefix="talk")
    parse_institution_talk(info, query)
    parse_online(info, query, prefix="talk")
    parse_offline(info, query, prefix="talk")
    parse_substring(info, query, "talk_keywords", ["abstract"])
    parse_access(info, query, prefix="talk")

    parse_substring(info, query, "speaker", ["speaker"])
    parse_substring(info, query, "affiliation", ["speaker_affiliation"])
    parse_substring(info, query, "title", ["title"])
    parse_date(info, query)
    parse_video(info, query)


def seminars_parser(info, query):
    parse_topic(info, query, prefix="seminar")
    parse_institution_sem(info, query)
    parse_online(info, query, prefix="seminar")
    parse_offline(info, query, prefix="seminar")
    parse_substring(info, query, "seminar_keywords", ["description", "comments"])
    parse_access(info, query, prefix="seminar")

    parse_substring(info, query, "name", ["name"])


# Common boxes


def institutions_shortnames():
    return sorted(db.institutions.search({}, projection=["shortname", "name"]), key=lambda elt: elt["name"])


textwidth = 400


class TalkSearchArray(SearchArray):
    noun = "talk"
    plural_noun = "talks"

    def __init__(self):
        ## topics
        topic = SelectBox(name="talk_topic", label="Topics", options=[("", "")] + topics())

        ## pick institution where it is held
        institution = SelectBox(
            name="talk_institution",
            label="Institution",
            options=[("", ""), ("None", "No institution", ),]
            + [(elt["shortname"], elt["name"]) for elt in institutions_shortnames()],
        )

        ## online only?
        online = CheckBox(name="talk_online", label="Online")
        offline = CheckBox(name="talk_offline", label="Offline")

        ## keywords for seminar or talk
        keywords = TextBox(
            name="talk_keywords",
            label="Keywords",
            colspan=(1, 2, 1),
            width=textwidth,
        )
        ## type of access
        access = SelectBox(
            name="talk_access",
            label="Access",
            options=[("", ""),
                     ("open", "Any visitor can view link"),
                     ("users", "Any logged-in user can view link")],
        )
        ## number of results to display
        # count = TextBox(name="talk_count", label="Results to display", example=50, example_value=True)

        speaker = TextBox(name="speaker", label="Speaker", colspan=(1, 2, 1), width=textwidth)
        affiliation = TextBox(
            name="affiliation",
            label="Affiliation",
            colspan=(1, 2, 1),
            width=160 * 2 - 1 * 20,
        )
        title = TextBox(name="title", label="Title", colspan=(1, 2, 1), width=textwidth)
        date = TextBox(
            name="daterange",
            id="daterange",
            label="Date",
            example=datetime.datetime.now(current_user.tz).strftime("%B %d, %Y -"),
            example_value=True,
            colspan=(1, 2, 1),
            width=160 * 2 - 1 * 20,
        )
        video = CheckBox(name="video", label="Has video")
        self.array = [
            [topic, keywords],
            [institution, title],
            [online, speaker],
            [offline],
            [access, affiliation],
            [video, date],
            # [count],
        ]

    def main_table(self, info=None):
        return self._print_table(self.array, info, layout_type="horizontal")

    def search_types(self, info):
        return [('talks', 'Search for talks')]

    def hidden(self, info):
        return [] # [("talk_start", "talk_start")]


class SemSearchArray(SearchArray):
    noun = "seminar"
    plural_noun = "seminars"

    def __init__(self):
        ## topics
        topic = SelectBox(name="seminar_topic", label="Topics", options=[("", "")] + topics())

        ## pick institution where it is held
        institution = SelectBox(
            name="seminar_institution",
            label="Institution",
            options=[("", ""), ("None", "No institution", ),]
            + [(elt["shortname"], elt["name"]) for elt in institutions_shortnames()],
        )

        ## online only?
        online = CheckBox(name="seminar_online", label="Online")
        offline = CheckBox(name="seminar_offline", label="Offline")

        ## keywords for seminar or talk
        keywords = TextBox(
            name="seminar_keywords",
            label="Keywords",
            colspan=(1, 2, 1),
            width=textwidth,
        )
        ## type of access
        access = SelectBox(
            name="seminar_access",
            label="Access",
            options=[("", ""),
                     ("open", "Any visitor can view link"),
                     ("users", "Any logged-in user can view link")],
        )
        ## number of results to display
        # count = TextBox(name="seminar_count", label="Results to display", example=50, example_value=True)

        name = TextBox(
            name="name", label="Name", colspan=(1, 2, 1), width=textwidth
        )

        self.array = [
            [topic, keywords],
            [institution, name],
            [online, access],
            # [count],
        ]

    def main_table(self, info=None):
        return self._print_table(self.array, info, layout_type="horizontal")

    def search_types(self, info):
        return [('seminars', 'Search for seminars')]

    def hidden(self, info):
        return [] # [("seminar_start", "seminar_start")]

@app.route("/")
def index():
    # Eventually want some kind of cutoff on which talks are included.
    talks = list(talks_search(
        {"display": True, "end_time": {"$gte": datetime.datetime.now()}},
        sort=["start_time"],
    ))
    topic_counts = Counter()
    for talk in talks:
        topic_counts["ALL"] += 1
        if talk.topics:
            for topic in talk.topics:
                topic_counts[topic] += 1
    #menu[0] = ("#", "$('#filter-menu').slideToggle(400); return false;", "Filter")
    return render_template(
        "browse.html",
        title="Math Seminars (beta)",
        topic_counts=topic_counts,
        talks=talks,
        section="Browse",
        toggle=toggle,
    )


@app.route("/search")
def search():
    info = to_dict(request.args,
                   seminar_search_array=SemSearchArray(),
                   talks_search_array=TalkSearchArray())
    if "search_type" not in info:
        info["talk_online"] = info["seminar_online"] = True
        info["daterange"] = info.get("daterange", datetime.datetime.now(current_user.tz).strftime("%B %d, %Y -"))
    try:
        seminar_count = int(info["seminar_count"])
        talk_count = int(info["talk_count"])
        seminar_start = int(info["seminar_start"])
        if seminar_start < 0:
            seminar_start += (1 - (seminar_start + 1) // seminar_count) * seminar_count
        talk_start = int(info["talk_start"])
        if talk_start < 0:
            talk_start += (1 - (talk_start + 1) // talk_count) * talk_count
    except (KeyError, ValueError):
        seminar_count = info["seminar_count"] = 50
        talk_count = info["talk_count"] = 50
        seminar_start = info["seminar_start"] = 0
        talk_start = info["talk_start"] = 0
    seminar_query = {}
    seminars_parser(info, seminar_query)
    info['seminar_results'] = seminars_search(seminar_query, sort=["weekday", "start_time", "name"]) # limit=seminar_count, offset=seminar_start,
    talk_query = {}
    talks_parser(info, talk_query)
    info['talk_results'] = talks_search(talk_query, sort=["start_time", "speaker"]) # limit=talk_count, offset=talk_start, 
    return render_template(
        "search.html",
        title="Search seminars",
        info=info,
        section="Search",
        bread=None,
    )


@app.route("/institutions/")
def list_institutions():
    section = "Manage" if current_user.is_creator() else None
    return render_template(
        "institutions.html",
        title="Institutions",
        section=section,
        subsection="institutions",
        institutions=institutions(),
    )


@app.route("/seminar/<shortname>")
def show_seminar(shortname):
    seminar = seminars_lucky({"shortname": shortname})
    if seminar is None:
        return render_template("404.html", title="Seminar not found")
    organizers = list(db.seminar_organizers.search({"seminar_id": shortname}))
    talks = talks_search({"display": True, "seminar_id": shortname}, projection=3)
    now = get_now()
    future = []
    past = []
    for talk in talks:
        if talk.end_time >= now:
            future.append(talk)
        else:
            past.append(talk)
    future.sort(key=lambda talk: talk.start_time)
    past.sort(key=lambda talk: talk.start_time, reverse=True)
    if current_user.email in seminar.editors() or current_user.is_admin():
        section = "Manage"
    else:
        section = None
    return render_template(
        "seminar.html",
        title="View seminar",
        future=future,
        past=past,
        seminar=seminar,
        section=section,
        subsection="view",
        bread=None,
    )

@app.route("/talk/<semid>/<int:talkid>/")
def show_talk(semid, talkid):
    token = request.args.get("token", "") # save the token so user can toggle between view and edit
    talk = talks_lucky({"seminar_id": semid, "seminar_ctr": talkid})
    if talk is None:
        return render_template("404.html", title="Talk not found")
    if (current_user.email_confirmed and
        (current_user.email in talk.seminar.editors() or
         current_user.email == talk.speaker_email) or
        current_user.is_admin()):
        section = "Manage"
    else:
        section = None
    return render_template(
        "talk.html",
        title="View talk",
        talk=talk,
        section=section,
        subsection='viewtalk',
        token=token,
    )


@app.route("/institution/<shortname>/")
def show_institution(shortname):
    institution = db.institutions.lookup(shortname)
    if institution is None:
        return render_template("404.html", title="Institution not found")
    institution = WebInstitution(shortname, data=institution)
    section = "Manage" if current_user.is_creator() else None
    return render_template(
        "institution.html",
        title="View institution",
        institution=institution,
        section=section,
        subsection="viewinst",
    )


@app.route("/subscribe")
def subscribe():
    # redirect to login page if not logged in, with message about what subscription is
    # If logged in, give a link to download the .ics file, the list of seminars/talks currently followed, and instructions on adding more
    return render_template(
        "subscribe.html", title="Subscribe", bread=None
    )
    raise NotImplementedError


@app.route("/info")
def info():
    return render_template("info.html", title="Info", section="Info")

@app.route("/faq")
def faq():
    return render_template("faq.html", title="FAQ")

#@app.route("/<topic>")
#def by_topic(topic):
#    # raise error if not existing topic?
#    return search({"seminars_topic": topic, "talks_topic": topic})
