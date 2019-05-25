#--depends-on commands

import json, re
from src import ModuleManager, utils

URL_GOOGLEBOOKS = "https://www.googleapis.com/books/v1/volumes"
URL_BOOKINFO = "https://books.google.co.uk/books?id=%s"
REGEX_BOOKID = re.compile("id=([\w\-]+)")

class Module(ModuleManager.BaseModule):
    _name = "ISBN"

    def get_book(self, query, event):
        page = utils.http.request(URL_GOOGLEBOOKS, get_params={
            "q": query, "country": "us"}, json=True)
        if page:
            if page.data["totalItems"] > 0:
                book = page.data["items"][0]["volumeInfo"]
                title = book["title"]
                sub_title = (", %s" % book.get("subtitle")
                    ) if book.get("subtitle") else ""

                authors = ", ".join(book.get("authors", []))
                authors = " - %s" % authors if authors else ""

                date = book.get("publishedDate", "")
                date = " (%s)" % date if date else ""

                rating = book.get("averageRating", -1)
                rating = " (%s/5.0)" % rating if not rating == -1 else ""

                id = re.search(REGEX_BOOKID, book["infoLink"]).group(1)
                info_link = " %s" % (URL_BOOKINFO % id)
                event["stdout"].write("%s%s%s%s%s%s" % (
                    title, authors, date, sub_title, info_link, rating))
            else:
                event["stderr"].write("Unable to find book")
        else:
            raise utils.EventsResultsError()

    @utils.hook("received.command.isbn", min_args=1)
    def isbn(self, event):
        """
        :help: Get book information from a provided ISBN
        :usage: <isbn>
        """
        isbn = event["args_split"][0]
        if len(isbn) == 10:
            isbn = "978%s" % isbn
        isbn = isbn.replace("-", "")
        self.get_book("isbn:%s" % isbn, event)

    @utils.hook("received.command.book", min_args=1)
    def book(self, event):
        """
        :help: Get book information from a provided title
        :usage: <book title>
        """
        self.get_book(event["args"], event)
