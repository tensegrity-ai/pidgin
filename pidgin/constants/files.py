"""File extension and path pattern constants."""


# File extensions
class FileExtensions:
    JSONL = ".jsonl"
    JSON = ".json"
    MARKDOWN = ".md"
    LOG = ".log"
    PID = ".pid"
    CSV = ".csv"
    YAML = ".yaml"
    YML = ".yml"
    DB = ".db"
    DUCKDB = ".duckdb"
    IPYNB = ".ipynb"


# Directory names
class DirectoryNames:
    EXPERIMENTS = "experiments"
    TRANSCRIPTS = "transcripts"
    ACTIVE = "active"
    LOGS = "logs"
    CONFIG = ".config"
    PIDGIN = "pidgin"


# File patterns
class FilePatterns:
    CONVERSATION_JSONL = "events.jsonl"
    MANIFEST_JSON = "manifest.json"
    TRANSCRIPT_MD = "transcript.md"
    PID_FILE = "{experiment_id}.pid"
    IMPORTED_MARKER = ".imported"
    IMPORTING_MARKER = ".importing"


# Special files
class SpecialFiles:
    MANIFEST = "manifest.json"
    CLAUDE_MD = "CLAUDE.md"
    PLANS_MD = "PLANS.md"
    README_MD = "README.md"


# Default paths
DEFAULT_OUTPUT_DIR = "pidgin"
DEFAULT_DB_NAME = "experiments.duckdb"
DEFAULT_CONFIG_FILE = "pidgin.yaml"
