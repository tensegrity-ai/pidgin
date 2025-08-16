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
    "[\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map symbols
    "\U0001f1e0-\U0001f1ff"  # flags
    "\U00002702-\U000027b0"  # dingbats
    "\U000024c2-\U0001f251"  # enclosed characters
    "\U0001f900-\U0001f9ff"  # supplemental symbols and pictographs
    "\U00002600-\U000026ff"  # miscellaneous symbols
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


# Convergence profiles and defaults
class ConvergenceProfiles:
    BALANCED = "balanced"
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    STRICT = "strict"
    CUSTOM = "custom"


class ConvergenceComponents:
    CONTENT = "content"
    STRUCTURE = "structure"
    SENTENCES = "sentences"
    LENGTH = "length"
    PUNCTUATION = "punctuation"


DEFAULT_CONVERGENCE_WEIGHTS = {
    ConvergenceProfiles.BALANCED: {
        ConvergenceComponents.CONTENT: 0.4,
        ConvergenceComponents.STRUCTURE: 0.15,
        ConvergenceComponents.SENTENCES: 0.2,
        ConvergenceComponents.LENGTH: 0.15,
        ConvergenceComponents.PUNCTUATION: 0.1,
    },
    ConvergenceProfiles.STRUCTURAL: {
        ConvergenceComponents.CONTENT: 0.25,
        ConvergenceComponents.STRUCTURE: 0.35,
        ConvergenceComponents.SENTENCES: 0.2,
        ConvergenceComponents.LENGTH: 0.1,
        ConvergenceComponents.PUNCTUATION: 0.1,
    },
    ConvergenceProfiles.SEMANTIC: {
        ConvergenceComponents.CONTENT: 0.6,
        ConvergenceComponents.STRUCTURE: 0.1,
        ConvergenceComponents.SENTENCES: 0.15,
        ConvergenceComponents.LENGTH: 0.1,
        ConvergenceComponents.PUNCTUATION: 0.05,
    },
    ConvergenceProfiles.STRICT: {
        ConvergenceComponents.CONTENT: 0.5,
        ConvergenceComponents.STRUCTURE: 0.25,
        ConvergenceComponents.SENTENCES: 0.15,
        ConvergenceComponents.LENGTH: 0.05,
        ConvergenceComponents.PUNCTUATION: 0.05,
    },
}

DEFAULT_CONVERGENCE_THRESHOLD = 0.8
DEFAULT_CONVERGENCE_ACTION = "warn"
DEFAULT_CONVERGENCE_PROFILE = "balanced"
