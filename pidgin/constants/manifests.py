"""Manifest file field names and structure constants."""

# Manifest field names
class ManifestFields:
    EXPERIMENT_ID = "experiment_id"
    NAME = "name"
    STATUS = "status"
    CONFIG = "config"
    CREATED_AT = "created_at"
    STARTED_AT = "started_at"
    COMPLETED_AT = "completed_at"
    TOTAL_CONVERSATIONS = "total_conversations"
    COMPLETED_CONVERSATIONS = "completed_conversations"
    FAILED_CONVERSATIONS = "failed_conversations"
    RUNNING_CONVERSATIONS = "running_conversations"
    CONVERSATIONS = "conversations"
    ERROR = "error"
    
    # Conversation entry fields
    class Conversation:
        CONVERSATION_ID = "conversation_id"
        JSONL = "jsonl"
        STATUS = "status"
        STARTED_AT = "started_at"
        COMPLETED_AT = "completed_at"
        ERROR = "error"
        TOTAL_TURNS = "total_turns"
        FINAL_CONVERGENCE = "final_convergence"

# Manifest version
MANIFEST_VERSION = "2.0"

# Required manifest fields
REQUIRED_MANIFEST_FIELDS = [
    ManifestFields.EXPERIMENT_ID,
    ManifestFields.NAME,
    ManifestFields.STATUS,
    ManifestFields.CONFIG,
    ManifestFields.CREATED_AT,
    ManifestFields.TOTAL_CONVERSATIONS,
]

# Manifest defaults
DEFAULT_MANIFEST_VALUES = {
    ManifestFields.COMPLETED_CONVERSATIONS: 0,
    ManifestFields.FAILED_CONVERSATIONS: 0,
    ManifestFields.RUNNING_CONVERSATIONS: 0,
    ManifestFields.CONVERSATIONS: {},
}