from pyaib.plugins import keyword, plugin_class, observe
from time import sleep
import requests


@plugin_class
class TTRSS(object):
    def __init__(self, irc_c, conf):
        self._should_run = False
        self._seen = []
        self.refresh_interval = conf.refresh_interval
        self.api = conf.ttrss_api
        self.channel = conf.channel
        self.user = conf.user
        self.password = conf.password
        self.yourls_api_url = conf.yourls_api_url
        self.yourls_signature = conf.yourls_signature

    def _login(self):
        json = {"op": "login", "user": self.user, "password": self.password}
        resp = requests.get(self.api, json=json).json()
        self._sid = resp["content"]["session_id"]

    def _make(self, json):
        if not self._sid:
            self._login()

        json["sid"] = self._sid

        return requests.get(self.api, json=json).json()

    def _run(self, irc_c):
        feeds = self._make({"op": "getHeadlines", "feed_id": -4})
        for item in feeds["content"]:
            self._seen.append(item["id"])

        while self._should_run:
            feeds = self._make({"op": "getHeadlines", "feed_id": -4})
            for item in feeds["content"]:
                if not item["id"] in self._seen:
                    self._seen.append(item["id"])
                    link = item["link"]

                    if self.yourls_api_url and self.yourls_signature:
                        p = {"signature": self.yourls_signature,
                             "action": "shorturl",
                             "format": "simple",
                             "url": link
                             }
                        link = requests.get(self.yourls_api_url, params=p).text

                    msg = "\x02{0}\x02: {1} [ {2} ]".format(item["feed_title"],
                                                            item["title"],
                                                            link)
                    irc_c.PRIVMSG(self.channel, msg)
                    sleep(1)
            sleep(self.refresh_interval)

    @keyword("start")
    def start(self, irc_c, msg, trigger, args, kargs):
        if self._should_run:
            msg.reply("Already running")
        else:
            msg.reply("Starting")
            self._should_run = True
            self._run(irc_c)

    @keyword("stop")
    def stop(self, irc_c, msg, trigger, args, kargs):
        if self._should_run:
            msg.reply("Stopping")
            self._should_run = False
        else:
            msg.reply("Already stopped")

    @observe('IRC_ONCONNECT')
    def onconnect(self, irc_c):
        irc_c.JOIN(self.channel)
        if not self._should_run:
            self._should_run = True
            self._login()

            self._run(irc_c)
