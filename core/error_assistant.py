import urllib.parse
import webbrowser
import json
import os


class ErrorAssistant:
    def __init__(self, config=None):
        self.search_sites = [
            "stackoverflow.com",
            "forum.xentax.com",
            "github.com",
            "zenhax.com",
            "gamedev.net"
        ]
        if config:
            custom = config.get("search_sites")
            if custom:
                self.search_sites = custom

    def generate_query(self, error, file_type=None, engine=None):
        site_query = " OR ".join(f"site:{s}" for s in self.search_sites)
        query = f"({site_query}) "
        if file_type:
            query += f'"{file_type}" '
        if engine:
            query += f'"{engine}" '
        clean = str(error).split(":")[-1].strip()
        query += f'"{clean}" fix solution'
        return query

    def get_search_url(self, error, file_type=None, engine=None):
        q = self.generate_query(error, file_type, engine)
        return f"https://www.google.com/search?q={urllib.parse.quote(q)}"

    def open_search(self, error, file_type=None, engine=None):
        url = self.get_search_url(error, file_type, engine)
        try:
            webbrowser.open(url)
        except:
            pass
        return url
