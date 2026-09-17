"""A tiny but complete bank: one question of every task type, used across the tests."""

LECTURE = (
    "Urban trees do far more than make streets look attractive. Researchers who measured temperatures across "
    "several cities found that neighbourhoods with dense canopy cover were up to four degrees cooler on summer "
    "afternoons. Trees also slow stormwater, because leaves intercept rain and roots help soil absorb it. "
    "Shade from mature trees can also lower the energy that households spend on air conditioning. "
    "However, the benefits are not shared equally. Wealthier suburbs usually have more trees, while older "
    "industrial areas have fewer. Planners in Melbourne and Auckland now map canopy cover street by street so "
    "that new planting can be targeted where heat risk is highest. The speaker concludes that tree planting "
    "should be treated as essential public infrastructure."
)

PASSAGE_MARKUP = (
    "Microplastics are fragments of plastic smaller than five millimetres. They {{enter|attend|contain|approach}} "
    "rivers and oceans from sources as varied as synthetic clothing, car tyres and cosmetic products. Because the "
    "particles are so small, they are {{readily|lately|hardly|rarely}} eaten by plankton and small fish, and from "
    "there they move up the food chain. Scientists are still debating how {{harmful|harmless|harming|harmed}} this "
    "is for human health, since long-term studies in people are difficult to design. What is clearer is that "
    "removing microplastics from water is costly, so most researchers argue that the most "
    "{{effective|expensive|excessive|exclusive}} response is to reduce plastic waste at its source. Several "
    "countries, including New Zealand, have already {{banned|required|promoted|encouraged}} microbeads in "
    "cosmetics."
)


def passage_body() -> str:
    from app.bank.markup import fill

    return fill(PASSAGE_MARKUP)


TURNS = [
    {"speaker": "Aroha", "text": "I think the university should move all first-year lectures online. Students could watch them at their own pace and replay difficult parts, which really helps people who are working part time."},
    {"speaker": "Ben", "text": "I see the flexibility, but attendance data shows that first-year students who come to campus are more likely to finish their degree. They build friendships and study groups, and that support matters most in the first year."},
    {"speaker": "Chen", "text": "Maybe we need a mix. Recorded lectures are useful for revision, but tutorials and labs should stay face to face. The university could also track which students stop engaging online and contact them early."},
    {"speaker": "Aroha", "text": "A blended model sounds fair, as long as the recordings are available to everyone from the first week."},
]


def sample_bank() -> tuple[list[dict], list[dict]]:
    sources = [
        {"source_key": "lec-urban-trees", "kind": "lecture", "title": "Urban trees", "body": LECTURE},
        {
            "source_key": "pas-microplastics", "kind": "passage", "title": "Microplastics",
            "body": passage_body(), "blank_markup": PASSAGE_MARKUP,
        },
        {
            "source_key": "dis-online-lectures", "kind": "discussion", "title": "Online first-year lectures",
            "body": "\n".join(f"{t['speaker']}: {t['text']}" for t in TURNS), "turns": TURNS,
        },
    ]
    lecture_keys = ["urban trees cool neighbourhoods", "trees slow stormwater", "benefits shared unequally", "planners map canopy cover"]
    questions = [
        {"type": "RA", "status": "active", "payload": {"text": "Volcanic soils are often remarkably fertile because they contain minerals released as ash and rock slowly weather. This is one reason farming communities have settled close to active volcanoes for thousands of years, despite the obvious risks."}},
        {"type": "RS", "status": "active", "payload": {"sentence": "The library will extend its opening hours during the examination period."}},
        {"type": "DI", "status": "active", "payload": {"chart": "bar", "title": "Average annual rainfall by city", "unit": " mm", "categories": ["Auckland", "Wellington", "Sydney", "Perth"], "min": 500, "max": 1400}},
        {"type": "RL", "source_key": "lec-urban-trees", "status": "active", "payload": {"key_points": lecture_keys}},
        {"type": "ASQ", "status": "active", "payload": {"question": "What instrument do doctors use to listen to a patient's heartbeat?", "accepted": ["stethoscope"]}},
        {"type": "SGD", "source_key": "dis-online-lectures", "status": "active", "payload": {"key_points": ["move first-year lectures online", "campus attendance helps students finish", "blended model with recordings"]}},
        {"type": "RTS", "status": "active", "payload": {"situation": "You borrowed a textbook from your classmate, Sam, and accidentally spilled coffee on several pages. Sam needs the book for an exam next week. Explain what happened and offer a solution.", "key_points": ["apologise to Sam", "explain coffee spilled on pages", "offer to replace or buy a new book"]}},
        {"type": "SWT", "source_key": "pas-microplastics", "status": "active", "payload": {"key_points": ["microplastics enter the food chain", "health effects still debated", "reduce plastic waste at source"]}},
        {"type": "WE", "status": "active", "payload": {"prompt": "Some people believe that governments should make public transport free for everyone. To what extent do you agree or disagree?", "key_points": ["free public transport", "cost to government", "congestion and environment"]}},
        {"type": "RWFIB", "source_key": "pas-microplastics", "status": "active", "payload": {}},
        {"type": "MCMA", "source_key": "pas-microplastics", "status": "active", "payload": {"question": "According to the passage, which of the following are true?", "options": ["Microplastics come from clothing and tyres.", "Plankton can eat microplastics.", "Removing microplastics from water is cheap.", "The health effects on people are fully understood.", "New Zealand has banned microbeads in cosmetics."], "answers": [0, 1, 4]}},
        {"type": "RO", "status": "active", "payload": {"paragraphs": ["The first public libraries in Australia opened in the nineteenth century.", "They were often funded by local councils and wealthy donors.", "These donors hoped that free reading would improve working people's education.", "Today, the same idea continues through free digital loans."]}},
        {"type": "RFIB", "source_key": "pas-microplastics", "status": "active", "payload": {"extra_words": ["rarely", "cheapest", "allowed"]}},
        {"type": "MCSA", "source_key": "pas-microplastics", "status": "active", "payload": {"question": "What do most researchers recommend?", "options": ["Filtering all seawater", "Reducing plastic waste at its source", "Banning synthetic clothing", "Studying plankton populations"], "answer": 1}},
        {"type": "SST", "source_key": "lec-urban-trees", "status": "backup", "payload": {"key_points": lecture_keys}},
        {"type": "LMCMA", "source_key": "lec-urban-trees", "status": "active", "payload": {"question": "Which benefits of urban trees does the speaker mention?", "options": ["Cooler temperatures", "Slower stormwater", "Higher property taxes", "Less traffic noise", "Better phone reception"], "answers": [0, 1]}},
        {"type": "LFIB", "source_key": "lec-urban-trees", "status": "active", "payload": {}},
        {"type": "HCS", "source_key": "lec-urban-trees", "status": "active", "payload": {"options": ["Urban trees lower temperatures and slow stormwater, but poorer areas have fewer trees, so planners now target planting where heat risk is highest.", "Urban trees are mainly decorative, and the speaker argues that cities should spend less on planting and more on roads.", "Trees in wealthy suburbs cause flooding because their roots damage soil, so planners in Melbourne are removing them."], "answer": 0}},
        {"type": "LMCSA", "source_key": "lec-urban-trees", "status": "active", "payload": {"question": "What is the speaker's main conclusion?", "options": ["Trees should be treated as essential infrastructure.", "Only wealthy suburbs need trees.", "Stormwater is not a real problem.", "Canopy maps are too expensive."], "answer": 0}},
        {"type": "SMW", "source_key": "lec-urban-trees", "status": "active", "payload": {"options": ["essential public infrastructure", "a private luxury", "an optional extra", "a temporary measure"], "answer": 0}},
        {"type": "HIW", "source_key": "lec-urban-trees", "status": "active", "payload": {"hiw_swaps": [["cooler", "warmer"], ["stormwater", "groundwater"], ["wealthier", "poorer"], ["Melbourne", "Sydney"], ["essential", "optional"]]}},
        {"type": "WFD", "status": "active", "payload": {"sentence": "Most students submit their assignments online before the deadline."}},
    ]
    return sources, questions
