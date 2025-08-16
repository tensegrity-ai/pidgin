"""State builder that uses manifests for efficient monitoring."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..io.logger import get_logger
from .state import ConversationParser, ManifestParser
from .state_types import ConversationState, ExperimentState

logger = get_logger("state_builder")


class StateBuilder:
    """Builds experiment state efficiently using manifest files.

    This class implements a caching mechanism to avoid repeated parsing of manifest
    files. It uses file modification times (mtime) to detect changes and invalidate
    the cache when necessary. The state builder coordinates between the manifest
    parser and conversation parser to build complete experiment states.

    The caching strategy significantly improves performance when monitoring multiple
    experiments, as manifest files only need to be re-parsed when they change.
    """

    def __init__(self) -> None:
        self.cache: Dict[Path, Tuple[float, ExperimentState]] = {}
        self.manifest_parser = ManifestParser()
        self.conversation_parser = ConversationParser()

    def get_experiment_state(self, exp_dir: Path) -> Optional[ExperimentState]:
        """Get experiment state from manifest with caching.

        Args:
            exp_dir: Experiment directory

        Returns:
            ExperimentState or None if not found
        """
        manifest_path = exp_dir / "manifest.json"

        # Check if manifest exists
        if not manifest_path.exists():
            return None

        # Check cache based on mtime
        try:
            current_mtime = manifest_path.stat().st_mtime
        except OSError:
            return None

        if exp_dir in self.cache:
            cached_mtime, cached_state = self.cache[exp_dir]
            if current_mtime == cached_mtime:
                logger.debug(f"Using cached state for {exp_dir.name}")
                return cached_state

        logger.debug(f"Building state for {exp_dir.name}")

        # Parse manifest with callbacks to conversation parser
        state = self.manifest_parser.parse_manifest(
            manifest_path=manifest_path,
            exp_dir=exp_dir,
            get_conversation_timestamps=self.conversation_parser.get_conversation_timestamps,
            get_last_convergence=self.conversation_parser.get_last_convergence,
            get_truncation_info=self.conversation_parser.get_truncation_info,
        )

        if state:
            # Update cache
            self.cache[exp_dir] = (current_mtime, state)

        return state

    def list_experiments(
        self, base_dir: Path, pattern: str = "*"
    ) -> List[ExperimentState]:
        """List all experiments in a directory.

        Args:
            base_dir: Base directory to search
            pattern: Glob pattern for experiment directories

        Returns:
            List of ExperimentState objects
        """
        experiments = []

        for exp_dir in sorted(base_dir.glob(pattern)):
            if not exp_dir.is_dir():
                continue

            # Check if it looks like an experiment directory
            if not (exp_dir / "manifest.json").exists():
                continue

            state = self.get_experiment_state(exp_dir)
            if state:
                experiments.append(state)

        return experiments

    def clear_cache(self) -> None:
        """Clear the state cache."""
        self.cache.clear()
        logger.debug("State cache cleared")

    def get_conversation_state(
        self, exp_dir: Path, conv_id: str
    ) -> Optional[ConversationState]:
        """Get state for a specific conversation.

        This method tries to get conversation state from:
        1. The experiment's manifest (if cached)
        2. Direct JSONL parsing if not in manifest

        Args:
            exp_dir: Experiment directory
            conv_id: Conversation ID

        Returns:
            ConversationState or None if not found
        """
        # First try to get from experiment state
        exp_state = self.get_experiment_state(exp_dir)
        if exp_state and conv_id in exp_state.conversations:
            return exp_state.conversations[conv_id]

        # If not found, try to build directly from JSONL
        return self.conversation_parser.get_conversation_state(exp_dir, conv_id)
