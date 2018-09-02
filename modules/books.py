import json, re
import Utils

URL_GOOGLEBOOKS = "https://www.googleapis.com/books/v1/volumes"
URL_BOOKINFO = "https://books.google.co.uk/books?id=%s"
REGEX_BOOKID = re.compile("id=([\w\-]+)")

class Module(object):
    _name = "ISBN"
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received").on("command").on("isbn").hook(
            self.isbn, help="Get book information from a provided ISBN",
            min_args=1, usage="<isbn>")
        events.on("received").on("command").on("book").hook(
            self.book, help="Get book information from a provided title",
            min_args=1, usage="<book title>")

    def get_book(self, query, event):
        page = Utils.get_url(URL_GOOGLEBOOKS, get_params={
            "q": query, "country": "us"}, json=True)
        if page:
            if page["totalItems"] > 0:
                book = page["items"][0]["volumeInfo"]
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
            event["stderr"].write("Failed to load results")

    def isbn(self, event):
        isbn = event["args_split"][0]
        if len(isbn) == 10:
            isbn = "978%s" % isbn
        isbn = isbn.replace("-", "")
        self.get_book("isbn:%s" % isbn, event)

    def book(self, event):
        self.get_book(event["args"], event)
