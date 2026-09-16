"""The 22 PTE Academic task types, with practice timing, instructions and tips.

Timing follows the published PTE Academic format. Reading and some listening tasks share a section
clock in the real test, so the answer time here is a sensible per-question practice budget.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskTypeDef:
    code: str
    name: str
    section: str
    prep_seconds: int
    answer_seconds: int
    ai_feedback: bool
    uses_source: str | None  # lecture, passage, discussion or None
    audio: bool  # plays audio before the answer phase
    replay: bool  # the student may replay the audio
    spoken: bool  # answered by speaking
    instructions: str
    tip: str


TYPES: list[TaskTypeDef] = [
    # Speaking and writing
    TaskTypeDef(
        "RA", "Read Aloud", "speaking_writing", 35, 40, True, None, False, False, True,
        "Look at the text below. When the recording starts, read the text aloud as naturally and clearly as you can. "
        "You have 35 seconds to prepare and 40 seconds to read.",
        "Use the prep time to spot tricky words and plan where to pause. Keep a steady pace. "
        "If you stumble, keep going rather than starting the sentence again.",
    ),
    TaskTypeDef(
        "RS", "Repeat Sentence", "speaking_writing", 0, 15, True, None, True, False, True,
        "You will hear a sentence. Repeat the sentence exactly as you heard it. You will hear the sentence only once.",
        "Listen for the meaning, not just the sounds, so you can rebuild the sentence in chunks. "
        "Start speaking as soon as the recording opens and keep your rhythm even.",
    ),
    TaskTypeDef(
        "DI", "Describe Image", "speaking_writing", 25, 40, True, None, False, False, True,
        "Look at the image below. In 25 seconds, please speak into the microphone and describe in detail what the "
        "image is showing. You will have 40 seconds to give your response.",
        "Use a simple plan: say what the chart shows, name the highest and lowest values, describe one trend, "
        "then finish with a short conclusion.",
    ),
    TaskTypeDef(
        "RL", "Retell Lecture", "speaking_writing", 10, 40, True, "lecture", True, False, True,
        "You will hear a lecture. After listening, you have 10 seconds to prepare and 40 seconds to retell the "
        "lecture in your own words.",
        "Note key words while you listen: the topic, two or three main points, and any conclusion. "
        "Link them with phrases like 'the speaker then explained'.",
    ),
    TaskTypeDef(
        "ASQ", "Answer Short Question", "speaking_writing", 0, 10, False, None, True, False, True,
        "You will hear a question. Please give a simple and short answer. Often just one or a few words is enough.",
        "Answer with the key word straight away. You don't need a full sentence.",
    ),
    TaskTypeDef(
        "SGD", "Summarize Group Discussion", "speaking_writing", 10, 120, True, "discussion", True, False, True,
        "You will hear a group discussion. After listening, you have 10 seconds to prepare and 2 minutes to "
        "summarize the discussion, including each speaker's main point.",
        "Track who said what. Give the topic first, then each speaker's view, then where the group agreed or disagreed.",
    ),
    TaskTypeDef(
        "RTS", "Respond to a Situation", "speaking_writing", 20, 40, True, None, True, False, True,
        "Listen to and read a description of a situation. You have 20 seconds to prepare and 40 seconds to give "
        "your response.",
        "Speak as if you are really in the situation. Greet the person, explain the problem, and suggest a clear "
        "next step. Keep your tone polite.",
    ),
    TaskTypeDef(
        "SWT", "Summarize Written Text", "speaking_writing", 0, 600, True, "passage", False, False, False,
        "Read the passage below and summarize it using one sentence. Type your response in the box. "
        "You have 10 minutes. Your response should be between 5 and 75 words.",
        "Write exactly one sentence with a clear main idea, then join supporting points with words like "
        "'while', 'because' or 'which'. Finish with one full stop.",
    ),
    TaskTypeDef(
        "WE", "Write Essay", "speaking_writing", 0, 1200, True, None, False, False, False,
        "You will have 20 minutes to plan, write and revise an essay about the topic below. Your response should be "
        "between 200 and 300 words.",
        "Plan four paragraphs: introduction with your position, two body paragraphs with examples, and a conclusion. "
        "Leave two minutes to check spelling.",
    ),
    # Reading
    TaskTypeDef(
        "RWFIB", "Reading & Writing: Fill in the Blanks", "reading", 0, 120, False, "passage", False, False, False,
        "Below is a text with blanks. Choose the best answer for each blank from the drop-down list.",
        "Read the whole sentence around each blank. Check grammar first (word form, tense, collocation), "
        "then meaning.",
    ),
    TaskTypeDef(
        "MCMA", "Reading: Multiple Choice, Multiple Answers", "reading", 0, 120, False, "passage", False, False, False,
        "Read the text and answer the question by selecting all the correct responses. More than one response is "
        "correct.",
        "Wrong choices cost you a point, so only pick options you can find support for in the text.",
    ),
    TaskTypeDef(
        "RO", "Reorder Paragraphs", "reading", 0, 150, False, None, False, False, False,
        "The text boxes below are in random order. Put them in the correct order.",
        "Find the opening sentence first: it usually introduces the topic without pronouns like 'this' or 'they'. "
        "Then link pairs using pronouns and connecting words.",
    ),
    TaskTypeDef(
        "RFIB", "Reading: Fill in the Blanks", "reading", 0, 120, False, "passage", False, False, False,
        "In the text below some words are missing. Drag words from the box below to the appropriate place in the "
        "text. There are more words than you need.",
        "Decide what part of speech each blank needs before you look at the word box.",
    ),
    TaskTypeDef(
        "MCSA", "Reading: Multiple Choice, Single Answer", "reading", 0, 90, False, "passage", False, False, False,
        "Read the text and answer the multiple-choice question by selecting the correct response. Only one response "
        "is correct.",
        "Rule out options that are too broad, too extreme, or not mentioned in the text.",
    ),
    # Listening
    TaskTypeDef(
        "SST", "Summarize Spoken Text", "listening", 0, 600, True, "lecture", True, False, False,
        "You will hear a short lecture. Write a summary for a fellow student who was not at the lecture. "
        "You should write 50 to 70 words. You have 10 minutes to finish this task.",
        "Write down the topic and main points while listening. Aim for about 60 words so you stay safely in range.",
    ),
    TaskTypeDef(
        "LMCMA", "Listening: Multiple Choice, Multiple Answers", "listening", 0, 90, False, "lecture", True, False, False,
        "Listen to the recording and answer the question by selecting all the correct responses. More than one "
        "response is correct.",
        "Read the question and options before the audio starts so you know what to listen for.",
    ),
    TaskTypeDef(
        "LFIB", "Listening: Fill in the Blanks", "listening", 0, 60, False, "lecture", True, False, False,
        "You will hear a recording. Type the missing words in each blank.",
        "Type what you hear as the audio plays, then fix spelling at the end. Spelling counts.",
    ),
    TaskTypeDef(
        "HCS", "Highlight Correct Summary", "listening", 0, 90, False, "lecture", True, False, False,
        "You will hear a recording. Select the paragraph that best relates to the recording.",
        "Wrong summaries often add a detail that wasn't said or change the speaker's conclusion.",
    ),
    TaskTypeDef(
        "LMCSA", "Listening: Multiple Choice, Single Answer", "listening", 0, 60, False, "lecture", True, False, False,
        "Listen to the recording and answer the multiple-choice question by selecting the correct response. "
        "Only one response is correct.",
        "Listen for the speaker's overall purpose as well as the details.",
    ),
    TaskTypeDef(
        "SMW", "Select Missing Word", "listening", 0, 60, False, "lecture", True, False, False,
        "You will hear a recording. At the end of the recording the last word or group of words has been replaced "
        "by a beep. Select the correct option to complete the recording.",
        "Focus on where the argument is heading in the final sentence. The missing words usually complete that idea.",
    ),
    TaskTypeDef(
        "HIW", "Highlight Incorrect Words", "listening", 0, 60, False, "lecture", True, False, False,
        "You will hear a recording. Below is a transcript of the recording. Some words in the transcript differ from "
        "what the speaker said. Please click on the words that are different.",
        "Follow the text with your eyes as the audio plays. Only click when you are sure, because wrong clicks lose a point.",
    ),
    TaskTypeDef(
        "WFD", "Write from Dictation", "listening", 0, 60, False, None, True, False, False,
        "You will hear a sentence. Type the sentence in the box below exactly as you hear it. "
        "Write as much of the sentence as you can. You will hear the sentence only once.",
        "Write the first letter of each word as you listen, then fill in the full words straight after.",
    ),
]

TYPES_BY_CODE: dict[str, TaskTypeDef] = {t.code: t for t in TYPES}
