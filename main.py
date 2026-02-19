botq = []

def add_bot(bot):
    botq.append(bot)


def remove_bot(bot):
    botq.remove(bot)


if __name__ == "__main__":
    add_bot("Bot1")
    add_bot("Bot2")
    add_bot("Bot3")
    print(botq)
