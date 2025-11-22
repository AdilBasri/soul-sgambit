from dataclasses import dataclass
import random
from typing import List, Optional


@dataclass(frozen=True)
class Card:
    """A simple immutable card with suit and rank (both strings)."""
    suit: str
    rank: str

    def __repr__(self) -> str:
        # Human-friendly representation
        return f"{self.rank} of {self.suit}"


class Deck:
    """Standard 52-card deck for Pygame projects.

    Suits: spades, clubs, diamonds, hearts
    Ranks: ace, 02..10, jack, queen, king

    Methods
    - shuffle(): shuffle the deck in place
    - draw(): remove and return the top card or None if empty
    - reset(): restore a new ordered 52-card deck
    """

    def __init__(self) -> None:
        # English lowercase suit names and zero-padded ranks as requested
        self._suits = ["spades", "clubs", "diamonds", "hearts"]
        self._ranks = [
            "ace",
            "02",
            "03",
            "04",
            "05",
            "06",
            "07",
            "08",
            "09",
            "10",
            "jack",
            "queen",
            "king",
        ]
        self.reset()

    def reset(self) -> None:
        """Create a fresh ordered 52-card deck (no shuffling)."""
        self.cards: List[Card] = [Card(s, r) for s in self._suits for r in self._ranks]

    def shuffle(self) -> None:
        """Shuffle the deck in place using random.shuffle."""
        random.shuffle(self.cards)

    def draw(self) -> Optional[Card]:
        """Draw (remove) and return the top card.

        Returns None if the deck is empty.
        """
        if not self.cards:
            return None
        # Treat index 0 as the top of the deck
        return self.cards.pop(0)
