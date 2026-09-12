import re

import chess

from chugg.views import PIECES


def test_all_twelve_pieces_are_present() -> None:
    assert sorted(PIECES) == sorted(
        f"{color}{chess.piece_symbol(kind).upper()}" for color in "wb" for kind in chess.PIECE_TYPES
    )


def test_markup_is_safe_to_inline_repeatedly() -> None:
    for code, markup in PIECES.items():
        assert markup.startswith('<svg class="piece" aria-hidden="true"')
        assert markup.count("<svg") == 1 and markup.rstrip().endswith("</svg>")
        identifiers = re.findall(r'\bid="([\w-]+)"', markup)
        references = [
            first or second
            for first, second in re.findall(r'url\(#([\w-]+)\)|href="#([\w-]+)"', markup)
        ]
        # Ids are namespaced by piece so identical ids never carry different content
        # when many pieces share one document, and every reference stays internal.
        assert identifiers and all(name.startswith(f"{code}-") for name in identifiers)
        assert references and all(name in identifiers for name in references)
