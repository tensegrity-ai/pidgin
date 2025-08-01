"""Cell creation logic extracted from NotebookGenerator."""

from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import nbformat
    from nbformat.v4 import new_code_cell, new_markdown_cell
    NBFORMAT_AVAILABLE = True
except ImportError:
    NBFORMAT_AVAILABLE = False
    nbformat = None
    new_code_cell = None
    new_markdown_cell = None

from ..io.logger import get_logger

logger = get_logger("notebook_cells")


class NotebookCells:
    """Handles creation of all notebook cells."""
    
    def _make_markdown_cell(self, content: str) -> Dict[str, Any]:
        """Create a markdown cell, handling missing nbformat."""
        if new_markdown_cell is None:
            return {"cell_type": "markdown", "source": content}
        return new_markdown_cell(content)
    
    def _make_code_cell(self, code: str) -> Dict[str, Any]:
        """Create a code cell, handling missing nbformat."""
        if new_code_cell is None:
            return {"cell_type": "code", "source": code}
        return new_code_cell(code)

    def create_title_cell(self, data: Dict[str, Any]) -> "nbformat.NotebookNode":
        """Create title and overview markdown cell.
        
        Args:
            data: Data dictionary containing manifest and other experiment data
            
        Returns:
            Jupyter notebook markdown cell
        """
        # Handle both old style (direct manifest) and new style (data dict)
        if "manifest" in data:
            manifest = data["manifest"]
        else:
            manifest = data
            
        exp_name = manifest.get("name", "Unknown Experiment")
        exp_id = manifest.get("experiment_id", "unknown")
        created_at = manifest.get("created_at", "")

        content = f"""# Experiment Analysis: {exp_name}

**Experiment ID**: `{exp_id}`
**Created**: {self.format_timestamp(created_at)}
**Status**: {manifest.get("status", "unknown")}

## Configuration
- **Agent A**: {manifest.get("configuration", {}).get("model_a", "unknown")}
- **Agent B**: {manifest.get("configuration", {}).get("model_b", "unknown")}
- **Max Turns**: {manifest.get("configuration", {}).get("max_turns", 0)}
- **Conversations**: {manifest.get("total_conversations", 0)}

This notebook provides automated analysis of the experiment results."""

        return self._make_markdown_cell(content)

    def create_setup_cell(self) -> "nbformat.NotebookNode":
        """Create setup and imports code cell.
        
        Returns:
            Jupyter notebook code cell
        """
        code = """# Import required libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path

# Set up plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Configure display options
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 100)
pd.set_option('display.float_format', '{:.3f}'.format)

# Define experiment directory
exp_dir = Path(".")
print(f"Analyzing experiment in: {exp_dir.resolve()}")"""

        return self._make_code_cell(code)

    def create_data_loading_cell(
        self,
        manifest_or_data: Dict[str, Any],
        turn_metrics_data: Optional[List[Dict]] = None,
        messages_data: Optional[List[Dict]] = None,
        conversations_data: Optional[List[Dict]] = None,
    ) -> "nbformat.NotebookNode":
        """Create data loading code cell.
        
        Args:
            manifest_or_data: Either manifest dict (old style) or data dict with manifest key (new style)
            turn_metrics_data: Turn metrics from database (old style, optional)
            messages_data: Messages from database (old style, optional)
            conversations_data: Conversations from database (old style, optional)
            
        Returns:
            Jupyter notebook code cell
        """
        # Handle both old style (separate args) and new style (data dict)
        if turn_metrics_data is not None or messages_data is not None or conversations_data is not None:
            # Old style - first arg is manifest, other args are data
            manifest = manifest_or_data
            turn_metrics_data = turn_metrics_data or []
            messages_data = messages_data or []
            conversations_data = conversations_data or []
        elif "manifest" in manifest_or_data:
            # New style - data dict
            manifest = manifest_or_data["manifest"]
            turn_metrics_data = manifest_or_data.get("metrics", [])
            messages_data = []  # Not provided in new style
            conversations_data = manifest_or_data.get("conversations", [])
        else:
            # Old style with only manifest
            manifest = manifest_or_data
            turn_metrics_data = []
            messages_data = []
            conversations_data = []
            
        exp_id = manifest.get("experiment_id", "unknown")

        code = f'''# Load experiment data from EventStore
experiment_id = "{exp_id}"

# Data loaded from EventStore at notebook generation time
turn_metrics_data = {turn_metrics_data}
messages_data = {messages_data}
conversations_data = {conversations_data}

# Convert to DataFrames
turn_metrics = pd.DataFrame(turn_metrics_data)
messages = pd.DataFrame(messages_data)
conversations = pd.DataFrame(conversations_data)

print(f"Loaded {{len(turn_metrics)}} turn metrics from {{len(conversations)}} conversations")

# Display basic info about the loaded data
if not turn_metrics.empty:
    print("Turn metrics columns:", list(turn_metrics.columns))
if not messages.empty:
    print("Messages columns:", list(messages.columns))
if not conversations.empty:
    print("Conversations columns:", list(conversations.columns))'''

        return self._make_code_cell(code)

    def create_statistics_cell(self) -> "nbformat.NotebookNode":
        """Create basic statistics code cell.
        
        Returns:
            Jupyter notebook code cell
        """
        code = """# Basic Statistics
if 'turn_metrics' in locals():
    # Summary statistics
    print("\\n=== Conversation Summary ===")
    print(f"Total conversations: {conversations.shape[0]}")
    print(f"Completed: {(conversations['status'] == 'completed').sum()}")
    print(f"Failed: {(conversations['status'] == 'failed').sum()}")

    # Turn statistics
    turns_per_conv = turn_metrics.groupby('conversation_id')['turn_number'].max() + 1
    print(f"\\nAverage turns per conversation: {turns_per_conv.mean():.1f}")
    print(f"Min turns: {turns_per_conv.min()}")
    print(f"Max turns: {turns_per_conv.max()}")

    # Convergence statistics
    if 'convergence_score' in turn_metrics.columns:
        print(f"\\nAverage convergence score: {turn_metrics['convergence_score'].mean():.3f}")
        print(f"Final convergence scores: {turn_metrics.groupby('conversation_id')['convergence_score'].last().mean():.3f}")"""

        return self._make_code_cell(code)

    def create_convergence_analysis_cell(self) -> "nbformat.NotebookNode":
        """Create convergence analysis visualization code cell.
        
        Returns:
            Jupyter notebook code cell
        """
        code = """# Convergence Analysis
if 'turn_metrics' in locals() and 'convergence_score' in turn_metrics.columns:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # 1. Convergence over turns (all conversations)
    ax = axes[0, 0]
    for conversation_id in turn_metrics['conversation_id'].unique()[:10]:  # First 10 conversations
        conv_data = turn_metrics[turn_metrics['conversation_id'] == conv_id]
        ax.plot(conv_data['turn_number'], conv_data['convergence_score'],
                alpha=0.5, linewidth=1)
    ax.set_xlabel('Turn Number')
    ax.set_ylabel('Convergence Score')
    ax.set_title('Convergence Trajectories (First 10 Conversations)')
    ax.grid(True, alpha=0.3)

    # 2. Average convergence by turn
    ax = axes[0, 1]
    avg_by_turn = turn_metrics.groupby('turn_number')['convergence_score'].agg(['mean', 'std'])
    ax.plot(avg_by_turn.index, avg_by_turn['mean'], 'b-', linewidth=2, label='Mean')
    ax.fill_between(avg_by_turn.index,
                     avg_by_turn['mean'] - avg_by_turn['std'],
                     avg_by_turn['mean'] + avg_by_turn['std'],
                     alpha=0.2, label='±1 STD')
    ax.set_xlabel('Turn Number')
    ax.set_ylabel('Average Convergence Score')
    ax.set_title('Average Convergence Across All Conversations')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Final convergence distribution
    ax = axes[1, 0]
    final_scores = turn_metrics.groupby('conversation_id')['convergence_score'].last()
    ax.hist(final_scores, bins=30, alpha=0.7, color='green', edgecolor='black')
    ax.axvline(final_scores.mean(), color='red', linestyle='--',
               label=f'Mean: {final_scores.mean():.3f}')
    ax.set_xlabel('Final Convergence Score')
    ax.set_ylabel('Count')
    ax.set_title('Distribution of Final Convergence Scores')
    ax.legend()

    # 4. Convergence components
    ax = axes[1, 1]
    components = ['vocabulary_overlap', 'structural_similarity', 'mutual_mimicry']
    component_cols = [col for col in components if col in turn_metrics.columns]
    if component_cols:
        final_components = turn_metrics.groupby('conversation_id')[component_cols].last()
        final_components.mean().plot(kind='bar', ax=ax)
        ax.set_ylabel('Average Score')
        ax.set_title('Average Final Component Scores')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    plt.show()"""

        return self._make_code_cell(code)

    def create_length_analysis_cell(self) -> "nbformat.NotebookNode":
        """Create message length analysis code cell.
        
        Returns:
            Jupyter notebook code cell
        """
        code = """# Message Length Analysis
if 'turn_metrics' in locals():
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))

    # Extract message lengths
    agent_a_lengths = turn_metrics['agent_a_message_length'] if 'agent_a_message_length' in turn_metrics else None
    agent_b_lengths = turn_metrics['agent_b_message_length'] if 'agent_b_message_length' in turn_metrics else None

    if agent_a_lengths is not None and agent_b_lengths is not None:
        # 1. Length distribution by agent
        ax = axes[0]
        ax.hist([agent_a_lengths, agent_b_lengths], bins=30, label=['Agent A', 'Agent B'],
                alpha=0.7, color=['blue', 'orange'])
        ax.set_xlabel('Message Length (characters)')
        ax.set_ylabel('Frequency')
        ax.set_title('Message Length Distribution by Agent')
        ax.legend()

        # 2. Length convergence over time
        ax = axes[1]
        length_diff = abs(agent_a_lengths - agent_b_lengths)
        avg_diff_by_turn = turn_metrics.groupby('turn_number').apply(
            lambda x: abs(x['agent_a_message_length'] - x['agent_b_message_length']).mean()
        )
        ax.plot(avg_diff_by_turn.index, avg_diff_by_turn.values, 'g-', linewidth=2)
        ax.set_xlabel('Turn Number')
        ax.set_ylabel('Average Length Difference')
        ax.set_title('Message Length Convergence Over Time')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

        # Statistics
        print(f"Average message length - Agent A: {agent_a_lengths.mean():.1f} chars")
        print(f"Average message length - Agent B: {agent_b_lengths.mean():.1f} chars")
        print(f"Length correlation: {agent_a_lengths.corr(agent_b_lengths):.3f}")"""

        return self._make_code_cell(code)

    def create_vocabulary_analysis_cell(self) -> "nbformat.NotebookNode":
        """Create vocabulary analysis code cell.
        
        Returns:
            Jupyter notebook code cell
        """
        code = """# Vocabulary Analysis
if 'turn_metrics' in locals() and 'vocabulary_size_a' in turn_metrics.columns:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # 1. Vocabulary growth
    ax = axes[0, 0]
    vocab_growth = turn_metrics.groupby('turn_number')[['vocabulary_size_a', 'vocabulary_size_b']].mean()
    vocab_growth.plot(ax=ax, marker='o')
    ax.set_xlabel('Turn Number')
    ax.set_ylabel('Average Vocabulary Size')
    ax.set_title('Vocabulary Growth Over Turns')
    ax.legend(['Agent A', 'Agent B'])
    ax.grid(True, alpha=0.3)

    # 2. Vocabulary overlap evolution
    ax = axes[0, 1]
    if 'vocabulary_overlap' in turn_metrics.columns:
        overlap_by_turn = turn_metrics.groupby('turn_number')['vocabulary_overlap'].mean()
        ax.plot(overlap_by_turn.index, overlap_by_turn.values, 'purple', linewidth=2)
        ax.set_xlabel('Turn Number')
        ax.set_ylabel('Vocabulary Overlap')
        ax.set_title('Vocabulary Overlap Evolution')
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)

    # 3. Unique word ratio
    ax = axes[1, 0]
    if 'unique_word_ratio_a' in turn_metrics.columns:
        unique_ratios = turn_metrics[['unique_word_ratio_a', 'unique_word_ratio_b']].mean()
        unique_ratios.plot(kind='bar', ax=ax, color=['blue', 'orange'])
        ax.set_ylabel('Unique Word Ratio')
        ax.set_title('Average Unique Word Ratio by Agent')
        ax.set_xticklabels(['Agent A', 'Agent B'], rotation=0)

    # 4. Repetition analysis
    ax = axes[1, 1]
    if 'repetition_a' in turn_metrics.columns:
        repetition_by_turn = turn_metrics.groupby('turn_number')[['repetition_a', 'repetition_b']].mean()
        repetition_by_turn.plot(ax=ax)
        ax.set_xlabel('Turn Number')
        ax.set_ylabel('Repetition Score')
        ax.set_title('Repetition Over Time')
        ax.legend(['Agent A', 'Agent B'])
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()"""

        return self._make_code_cell(code)

    def create_advanced_metrics_markdown_cell(self) -> "nbformat.NotebookNode":
        """Create markdown explanation about advanced metrics.
        
        Returns:
            Jupyter notebook markdown cell
        """
        content = """## Advanced Metrics (Post-Processing)

The following metrics are stored as placeholders (0.0) in the database and can be calculated post-hoc:

### Semantic & Linguistic Metrics
- **semantic_similarity**: Requires sentence-transformers (~500MB with models)
- **sentiment_convergence**: Requires TextBlob or VADER sentiment analysis
- **emotional_intensity**: Requires NRCLex or similar emotion lexicons
- **formality_convergence**: Requires linguistic formality markers analysis

### Advanced Convergence Metrics
- **topic_consistency**: Requires topic modeling (LDA, BERT-based models)
- **rhythm_convergence**: Requires prosodic analysis tools
- **convergence_velocity**: Rate of change in convergence metrics

These metrics are intentionally not calculated by Pidgin to keep it lightweight and focused on conversation orchestration. Researchers can calculate them using the raw message text stored in the database.

### Example: Calculating Semantic Similarity

Here's how you might calculate semantic similarity post-hoc:"""

        return self._make_markdown_cell(content)

    def create_advanced_metrics_code_cell(self) -> "nbformat.NotebookNode":
        """Create code example for calculating advanced metrics.
        
        Returns:
            Jupyter notebook code cell
        """
        code = """# Example: Calculate semantic similarity for a conversation
# Note: This requires installing sentence-transformers: pip install sentence-transformers

# Uncomment to run:
# from sentence_transformers import SentenceTransformer
# import numpy as np
#
# # Load a pre-trained model
# model = SentenceTransformer('all-MiniLM-L6-v2')
#
# # Get messages for a specific conversation
# if 'turn_metrics' in locals():
#     sample_conv = turn_metrics['conversation_id'].iloc[0]
#     conv_turns = turn_metrics[turn_metrics['conversation_id'] == sample_conv]
#
#     # Calculate embeddings for each turn
#     semantic_similarities = []
#
#     for _, turn in conv_turns.iterrows():
#         # Get message texts (you would need to join with messages table)
#         msg_a = turn.get('agent_a_message', '')  # Would need actual message text
#         msg_b = turn.get('agent_b_message', '')
#
#         if msg_a and msg_b:
#             # Encode messages
#             embeddings = model.encode([msg_a, msg_b])
#
#             # Calculate cosine similarity
#             similarity = np.dot(embeddings[0], embeddings[1]) / (
#                 np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
#             )
#             semantic_similarities.append(similarity)
#
#     # Add to your analysis
#     conv_turns['semantic_similarity_calculated'] = semantic_similarities
#     print(f"Average semantic similarity: {np.mean(semantic_similarities):.3f}")

# For now, these metrics remain at 0.0 in the database
print("Advanced metrics are placeholders. Use the example above as a starting point for post-hoc analysis.")"""

        return self._make_code_cell(code)

    def create_turn_visualization_cell(self) -> "nbformat.NotebookNode":
        """Create turn-by-turn visualization code cell.
        
        Returns:
            Jupyter notebook code cell
        """
        code = """# Turn-by-Turn Metrics Visualization
if 'turn_metrics' in locals():
    # Select a sample conversation for detailed view
    sample_conv_id = turn_metrics['conversation_id'].iloc[0]
    sample_data = turn_metrics[turn_metrics['conversation_id'] == sample_conv_id]

    # Create comprehensive metrics plot
    metrics_to_plot = [
        'convergence_score', 'vocabulary_overlap', 'structural_similarity',
        'mutual_mimicry', 'agent_a_message_length', 'agent_b_message_length'
    ]

    available_metrics = [m for m in metrics_to_plot if m in sample_data.columns]

    if available_metrics:
        fig, axes = plt.subplots(len(available_metrics), 1,
                                figsize=(12, 3*len(available_metrics)),
                                sharex=True)

        if len(available_metrics) == 1:
            axes = [axes]

        for i, metric in enumerate(available_metrics):
            ax = axes[i]
            ax.plot(sample_data['turn_number'], sample_data[metric],
                   marker='o', linewidth=2)
            ax.set_ylabel(metric.replace('_', ' ').title())
            ax.grid(True, alpha=0.3)

            if i == 0:
                ax.set_title(f'Sample Conversation Metrics: {sample_conv_id[:8]}...')

        axes[-1].set_xlabel('Turn Number')
        plt.tight_layout()
        plt.show()

    # Display sample messages if available
    if 'messages' in locals():
        sample_messages = messages[messages['conversation_id'] == sample_conv_id].head(10)
        print(f"\\nFirst 10 messages from conversation {sample_conv_id[:8]}:")
        for _, msg in sample_messages.iterrows():
            print(f"\\n[{msg['role']}]: {msg['content'][:100]}...")"""

        return self._make_code_cell(code)

    def create_export_cell(self) -> "nbformat.NotebookNode":
        """Create data export options code cell.
        
        Returns:
            Jupyter notebook code cell
        """
        code = """# Export Options
# Export key metrics to CSV for further analysis
if 'turn_metrics' in locals():
    # Summary by conversation
    conv_summary = turn_metrics.groupby('conversation_id').agg({
        'turn_number': 'max',
        'convergence_score': ['mean', 'last'],
        'vocabulary_overlap': 'mean',
        'structural_similarity': 'mean'
    }).round(3)

    # Save to CSV
    conv_summary.to_csv('conversation_summary.csv')
    print("Saved conversation summary to 'conversation_summary.csv'")

    # Display summary
    print("\\nConversation Summary:")
    print(conv_summary.head(10))

# Create a comprehensive report
if 'conversations' in locals():
    report = {
        'total_conversations': len(conversations),
        'completed': (conversations['status'] == 'completed').sum(),
        'average_turns': turn_metrics.groupby('conversation_id')['turn_number'].max().mean() + 1,
        'average_convergence': turn_metrics['convergence_score'].mean() if 'convergence_score' in turn_metrics else None,
        'final_convergence': turn_metrics.groupby('conversation_id')['convergence_score'].last().mean() if 'convergence_score' in turn_metrics else None
    }

    print("\\n=== Experiment Report ===")
    for key, value in report.items():
        if value is not None:
            print(f"{key}: {value:.3f}" if isinstance(value, float) else f"{key}: {value}")"""

        return self._make_code_cell(code)

    def format_timestamp(self, timestamp: str) -> str:
        """Format ISO timestamp to readable format.
        
        Args:
            timestamp: ISO format timestamp string
            
        Returns:
            Formatted timestamp string
        """
        if not timestamp:
            return "Unknown"
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, AttributeError):
            return timestamp