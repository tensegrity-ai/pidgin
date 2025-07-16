"""Linguistic constants and patterns for metric calculations."""

import re

# Linguistic markers
HEDGE_WORDS = {
    "maybe",
    "perhaps",
    "possibly",
    "probably",
    "might",
    "could",
    "seems",
    "appears",
    "suggests",
    "somewhat",
    "fairly",
    "quite",
    "rather",
    "sort of",
    "kind of",
    "basically",
    "essentially",
    "generally",
    "typically",
    "usually",
    "arguably",
    "approximately",
    "roughly",
    "about",
    "around",
    "likely",
    "presumably",
    "conceivably",
    "potentially",
    "virtually",
    "practically",
}

AGREEMENT_MARKERS = {
    "yes",
    "yeah",
    "yep",
    "sure",
    "agreed",
    "agree",
    "exactly",
    "precisely",
    "absolutely",
    "definitely",
    "certainly",
    "indeed",
    "right",
    "correct",
    "true",
    "affirmative",
    "of course",
    "naturally",
    "obviously",
    "totally",
    "completely",
    "entirely",
    "undoubtedly",
    "clearly",
}

DISAGREEMENT_MARKERS = {
    "no",
    "nope",
    "not",
    "disagree",
    "wrong",
    "incorrect",
    "false",
    "but",
    "however",
    "although",
    "though",
    "actually",
    "conversely",
    "contrary",
    "unfortunately",
    "negative",
    "nah",
    "doubt",
    "doubtful",
    "nevertheless",
    "nonetheless",
    "alternatively",
    "rather",
    "instead",
    "oppose",
    "reject",
}

POLITENESS_MARKERS = {
    "please",
    "thank",
    "thanks",
    "sorry",
    "excuse",
    "pardon",
    "appreciate",
    "grateful",
    "kindly",
    "respectfully",
    "humbly",
    "graciously",
    "sincerely",
    "apologize",
    "apologies",
    "forgive",
    "regret",
    "welcome",
}

# Pronoun sets
FIRST_PERSON_SINGULAR = {"i", "me", "my", "mine", "myself"}
FIRST_PERSON_PLURAL = {"we", "us", "our", "ours", "ourselves"}
SECOND_PERSON = {"you", "your", "yours", "yourself", "yourselves"}
THIRD_PERSON_SINGULAR = {
    "he",
    "him",
    "his",
    "himself",
    "she",
    "her",
    "hers",
    "herself",
    "it",
    "its",
    "itself",
}
THIRD_PERSON_PLURAL = {"they", "them", "their", "theirs", "themselves"}

# Unicode symbol sets
ARROWS = {
    "→",
    "←",
    "↔",
    "⇒",
    "⇐",
    "⇔",
    "➜",
    "➡",
    "⬅",
    "↑",
    "↓",
    "⬆",
    "⬇",
    "↖",
    "↗",
    "↘",
    "↙",
}
MATH_SYMBOLS = {
    "≈",
    "≡",
    "≠",
    "≤",
    "≥",
    "±",
    "×",
    "÷",
    "∞",
    "∑",
    "∏",
    "∂",
    "∇",
    "√",
    "∫",
    "∈",
    "∉",
    "∀",
    "∃",
    "∅",
    "^",
    "+",
    "=",
    "<",
    ">",
    "*",
    "/",
    "%",
    "-",
}
BOX_DRAWING = {
    "┌",
    "┐",
    "└",
    "┘",
    "─",
    "│",
    "├",
    "┤",
    "┬",
    "┴",
    "┼",
    "═",
    "║",
    "╔",
    "╗",
    "╚",
    "╝",
}
BULLETS = {
    "•",
    "◦",
    "▪",
    "▫",
    "■",
    "□",
    "▲",
    "△",
    "▼",
    "▽",
    "◆",
    "◇",
    "○",
    "●",
    "★",
    "☆",
}

# Combine all special symbols for easy checking
ALL_SPECIAL_SYMBOLS = ARROWS | MATH_SYMBOLS | BOX_DRAWING | BULLETS

# Regex patterns
EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # enclosed characters
    "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    "\U00002600-\U000026FF"  # miscellaneous symbols
    "]+",
    flags=re.UNICODE,
)

# Include ASCII arrow patterns along with Unicode arrows
ARROW_PATTERN = re.compile(
    r"(?:->|<-|<->|=>|<=|<=>|[" + "".join(re.escape(c) for c in ARROWS) + "])"
)
MATH_PATTERN = re.compile(r"[" + "".join(re.escape(c) for c in MATH_SYMBOLS) + "]")
BOX_PATTERN = re.compile(r"[" + "".join(re.escape(c) for c in BOX_DRAWING) + "]")
BULLET_PATTERN = re.compile(r"[" + "".join(re.escape(c) for c in BULLETS) + "]")

# Sentence ending patterns
SENTENCE_ENDINGS = re.compile(r"[.!?]+")
QUESTION_PATTERN = re.compile(r"\?")
EXCLAMATION_PATTERN = re.compile(r"!")

# URL and email patterns
URL_PATTERN = re.compile(r"https?://[^\s]+|www\.[^\s]+")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

# Acknowledgment patterns for start of message
ACKNOWLEDGMENT_PATTERNS = [
    r"^(yes|yeah|yep|sure|okay|ok|right|correct|agreed|indeed)",
    r"^(ah|oh|hmm|hm|well|so|now|alright)",
    r"^(i see|i understand|i agree|got it|makes sense|understood)",
    r"^(thank|thanks|appreciate)",
    r"^(good|great|excellent|perfect|wonderful)",
]

# Compile acknowledgment patterns
ACKNOWLEDGMENT_REGEX = re.compile("|".join(ACKNOWLEDGMENT_PATTERNS), re.IGNORECASE)
