import json
import Utils

URL_GOOGLEBOOKS = "https://www.googleapis.com/books/v1/volumes"

class Module(object):
    _name = "ISBN"
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("isbn").hook(
            self.isbn, help="Get book information from a provided ISBN",
            min_args=1)

    def isbn(self, event):
        isbn = event["args_split"][0]
        if len(isbn) == 10:
            isbn = "978%s" % isbn
        isbn = isbn.replace("-", "")
        page = Utils.get_url(URL_GOOGLEBOOKS, get_params={
            "q": "isbn:%s" % isbn, "country": "us"}, json=True)
        if page:
            if page["totalItems"] > 0:
                book = page["items"][0]["volumeInfo"]
                title = book["title"]
                sub_title = book["subtitle"]
                authors = ", ".join(book["authors"])
                date = book["publishedDate"]
                rating = book["averageRating"]
                #language = book["language"]
                event["stdout"].write("%s - %s (%s), %s (%s/5.0)" % (
                    title, authors, date, sub_title, rating))
            else:
                event["stderr"].write("Unable to find book")
        else:
            event["stderr"].write("Failed to load results")
