"""Linguistic constants and patterns for analysis."""

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

# Combine all pronouns
ALL_PRONOUNS = (
    FIRST_PERSON_SINGULAR
    | FIRST_PERSON_PLURAL
    | SECOND_PERSON
    | THIRD_PERSON_SINGULAR
    | THIRD_PERSON_PLURAL
)

# Sentence ending patterns (for regex)
SENTENCE_ENDINGS_PATTERN = r"[.!?]+"
QUESTION_PATTERN = r"\?"
EXCLAMATION_PATTERN = r"!"

# URL and email patterns (for regex)
URL_PATTERN = r"https?://[^\s]+|www\.[^\s]+"
EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

# Acknowledgment patterns for start of message
ACKNOWLEDGMENT_PATTERNS = [
    r"^(yes|yeah|yep|sure|okay|ok|right|correct|agreed|indeed)",
    r"^(ah|oh|hmm|hm|well|so|now|alright)",
    r"^(i see|i understand|i agree|got it|makes sense|understood)",
    r"^(thank|thanks|appreciate)",
    r"^(good|great|excellent|perfect|wonderful)",
]
