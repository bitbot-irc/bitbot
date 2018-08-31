import random

QUOTES = {
    "You can build a throne with bayonets, but it's difficult to sit on it.": "Boris Yeltsin",
    "We don't appreciate what we have until it's gone. Freedom is like that. It's like air. When you have it, you don't notice it.": "Boris Yeltsin",
    "They accused us of suppressing freedom of expression. This was a lie and we could not let them publish it.": "Nelba Blandon, as director of censorship, Nicaragua",
    "Death solves all problems - no man, no problem.": "Anatoly Rybakov",
    "If we don't end war, war will end us.": "H.G. Wells",
    "All that is necessary for evil to succeed is for good men to do nothing.": "Edmund Burke",
    "Live well. It is the greatest revenge.": "The Talmud",
    "To improve is to change, so to be perfect is to have changed often.": "Winston Churchill",
    "I believe it is peace for our time.": "Neville Chamberlain",
    "Orbiting Earth in the spaceship, I saw how beautiful our planet is. People, let us preserve and increase this beauty, not destroy it!": "Yuri Gagarin",
    "Science is not everything, but science is very beautiful.": "Robert Oppenheimer",
    "We choose to go to the Moon! We choose to go to the Moon in this decade and do the other things, not because they are easy, but because they are hard.": "",
    "You teach a child to read, and he or her will be able to pass a literacy test.": "George W Bush",
    "I know the human being and fish can coexist peacefully.": "George W Bush",
    "They misunderestimated me.": "George W Bush",
    "I'm an Internet expert too.": "Kim Jong Il",
    "So long, and thanks for all the fish": "",
    "It is a lie that I made the people starve.": "Nicolae Ceaușescu",
    "As far as I know - effective immediately, without delay.": "Günter Schabowski",
    "Not all those who wander are lost.": "J.R.R. Tolkien",
    "Life would be tragic if it weren't funny.": "Stephen Hawking",
    "We are such stuff as dreams are made on; and our little life is rounded with a sleep.": "",
    "Do androids dream of electric sheep?": "",
    "Love all, trust a few, do wrong to none.": "William Shakespeare",
    "Patriotism is not enough. I must have no hatred or bitterness towards any one.": "Edith Cavell",
    "The monuments of wit survive the monuments of power.": "Francis Bacon",
    "Human ingenuity cannot concoct a cipher which human ingenuity cannot resolve": "Edgar Allan Poe",
    "Nobody has the intention to erect a wall": "Walter Ulbricht",
    "We're all completely fucked. I'm fucked. You're fucked. [...] It has been the biggest cock-up ever and we're all completely fucked": "Richard Mottram",
    "The security aspect of cyber is very, very tough. And maybe it's hardly doable.": "Donald Trump",
    "The Internet. The hate machine, the love machine, the machine powered by many machines. We are all part of it, helping it grow, and helping it grow on us.": "Topiary",
    "Every great historical event began as a utopia and ended as a reality.": "Richard Nikolaus Eijiro",
    "Strange women lying in ponds distributing swords is no basis for a system of government!": "",
    "My hovercraft is full of eels.": "",
    "That was only a prelude; where they burn books, they will in the end also burn people": "Heinrich Heine",
    'Never, "for the sake of peace and quiet", deny your own experience or convictions.': "Dag Hammarskjöld",
    "Quis custodiet ipsos custodes?": "",
    "Unless someone like you cares a whole awful lot, nothing is going to get better. It's not.": "Theodor Seuss Geisel",
    "Wer nichts zu verbergen hat, hat auch nichts zu befürchten": "",
    "Words will always retain their power. Words offer the means to meaning, and for those who will listen, the enunciation of truth.": "Alan Moore",
    "Сейчас я вам заявляю, что вы провалились!": "",
    "Godhet är något så enkelt: att alltid finnas för andra, att aldrig söka sig själv.": "Dag Hammarskjöld",
    "Fire, water and government know nothing of mercy": "",
    "The optimist proclaims that we live in the best of all possible worlds; and the pessimist fears this is true. So I elect for neither label": "James Branch Cabell",
    "微乎微乎，至于无形；神乎神乎，至于无声；故能为敌之司命": "孫子",
    "If you know your enemy and know yourself, one hundred battles will not defeat you": "Sun Tzu",
    "Come here to this gate! Mr Gorbachev, open this gate! Mr Gorbachev, tear down this wall!": "Ronald Reagan",
    "The lamps are going out all over Europe, we shall not see them lit again in our lifetime": "Edward Grey",
    "The laws of mathematics are very commendable, but the only law that applies in Australia is the law of Australia": "Malcolm Turnbull",
    "He had to download the entire iOS system on his computer, he had to decrypt it, he had to do all of these things I don't even understand": "Glenn Moramarco, as assistant U.S. attorney",
    "I don’t need to understand how encryption works": "Amber Rudd",
}


class Module(object):
    def __init__(self, bot):
        bot.events.on("get.quit-quote").hook(self.quote)

    def quote(self, event):
        quote = random.choice(list(QUOTES.items()))
        return (" - " if quote[1] else "").join(quote)
