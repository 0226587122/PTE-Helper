"""British and Australian spellings, derived from an American word list.

The bundled dictionary is American only: it has "color" but not "colour", "defense" but not
"defence". PTE Academic accepts British, Australian and American spelling, and most of our students
sit the test in Australia, so marking "colour" wrong would be worse than useless.

Rather than vendoring a licensed Hunspell dictionary, the British and Australian forms are generated
from the American ones by the regular correspondences, plus a table of irregulars that no rule
catches. Generation only ever *adds* accepted spellings. Over-generating means quietly accepting a
rare non-word, which is a far smaller harm than telling a student that "organise" is a mistake.
"""

import re

# Regular correspondences, as (American ending, British ending). Order does not matter: every rule
# that matches a word contributes a form.
_ENDINGS: tuple[tuple[str, str], ...] = (
    ("ize", "ise"),
    ("izes", "ises"),
    ("ized", "ised"),
    ("izing", "ising"),
    ("izer", "iser"),
    ("izers", "isers"),
    ("ization", "isation"),
    ("izations", "isations"),
    ("yze", "yse"),
    ("yzes", "yses"),
    ("yzed", "ysed"),
    ("yzing", "ysing"),
    ("ter", "tre"),
    ("ters", "tres"),
    ("ber", "bre"),
    ("bers", "bres"),
    ("nse", "nce"),
    ("nses", "nces"),
    ("og", "ogue"),
    ("ogs", "ogues"),
    ("eled", "elled"),
    ("eling", "elling"),
    ("eler", "eller"),
    ("elers", "ellers"),
)

# "-or" to "-our" only applies to this family. Applying it to every word ending in "-or" would
# accept "doctour", "actour" and "errour".
_OUR_STEMS = tuple(
    sorted(
        """
        color behavior favor flavor harbor honor humor labor neighbor odor rumor savor splendor vapor vigor
        armor endeavor parlor valor candor clamor tremor demeanor
        """.split(),
        key=len,
        reverse=True,
    )
)

# The "u" survives in front of these endings but not others: "colourful" and "neighbourhood" keep
# it, while "coloration", "humorous", "honorary" and "laboratory" drop it in British English too.
_OUR_SUFFIXES = frozenset(
    ["", "s", "ed", "ing", "er", "ers", "ful", "fully", "less", "lessly", "ly", "hood", "hoods",
     "able", "ably", "ite", "ites", "al", "ally", "ist", "ists", "ise", "ises", "ised", "ising"]
)

# "-ter" to "-tre" and "-ber" to "-bre" likewise: "center" becomes "centre", but "water" must not
# become "watre".
_RE_WORDS = frozenset(
    """
    center centers theater theaters liter liters meter meters fiber fibers caliber calibers somber
    scepter specter sceptres luster
    """.split()
)

# "-nse" to "-nce" applies to this handful only, or "sense" would become "sence".
_NCE_WORDS = frozenset("defense defenses offense offenses pretense pretenses license licenses".split())

# "-og" to "-ogue": "catalog" becomes "catalogue", but "dog" must not become "dogue".
_OGUE_WORDS = frozenset("catalog catalogs dialog dialogs monolog monologs analog epilog prolog".split())

# Irregulars: British and Australian spellings no rule produces, and words the American list omits.
IRREGULARS = frozenset(
    """
    programme programmes grey greyer greyish tyre tyres kerb kerbs plough ploughs ploughed ploughing
    mould moulds moulded mouldy smoulder smoulders smouldering storey storeys aluminium sulphur sulphuric
    cheque cheques draught draughts gaol jewellery jewelled practise practises practised practising
    licence licences offence offences pretence pretences dialogue dialogues monologue monologues
    analogue analogues epilogue prologue travelling traveller travellers cancelled cancelling
    labelled labelling signalled signalling fuelled fuelling marvellous skilful wilful fulfil fulfils
    enrol enrols enrolment instalment instil distil councillor councillors counsellor counsellors
    jeweller sceptre sceptres spectre spectres calibre calibres fibre fibres litre litres metre metres
    centre centres centred centring theatre theatres sombre lustre manoeuvre manoeuvres foetus foetal oesophagus
    anaemia anaemic anaesthetic anaesthesia archaeology archaeological palaeontology encyclopaedia
    orthopaedic paediatric paediatrics haemoglobin diarrhoea leukaemia
    axe axes moustache doughnut whisky pyjamas cosy kilometre kilometres millimetre millimetres
    centimetre centimetres litre-sized behaviours labours neighbours colours favours flavours honours
    humours odours rumours vapours armours
    """.split()
)


def british_variants(word: str) -> set[str]:
    """The British and Australian forms of one American word. Empty when no rule applies."""
    out: set[str] = set()
    for stem in _OUR_STEMS:
        if word.startswith(stem) and word[len(stem) :] in _OUR_SUFFIXES:
            out.add(stem[:-2] + "our" + word[len(stem) :])
            break

    for american, british in _ENDINGS:
        if not word.endswith(american):
            continue
        stem = word[: -len(american)]
        if american.startswith(("ter", "ber")):
            if word not in _RE_WORDS:
                continue
        elif american.startswith("nse"):
            if word not in _NCE_WORDS:
                continue
        elif american.startswith("og"):
            if word not in _OGUE_WORDS:
                continue
        elif american.startswith(("ize", "izes", "ized", "izing")) and len(stem) < 2:
            # "size" and "prize" are not "sise" and "prise".
            continue
        elif american.startswith("ize") and re.search(r"(s|pr)$", stem):
            continue
        out.add(stem + british)
    return out


def expand(american_words: set[str] | frozenset[str]) -> set[str]:
    """Every British and Australian form generated from an American word list, plus the irregulars."""
    out: set[str] = set(IRREGULARS)
    for word in american_words:
        out |= british_variants(word)
    return out
