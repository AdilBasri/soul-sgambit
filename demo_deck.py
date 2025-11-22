from deck import Deck


def main() -> None:
    d = Deck()
    print("Initial count:", len(d.cards))
    d.shuffle()
    c = d.draw()
    print("Drew:", c)
    print("Remaining:", len(d.cards))


if __name__ == '__main__':
    main()
