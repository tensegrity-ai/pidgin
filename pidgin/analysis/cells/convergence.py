"""Convergence analysis cells for notebooks."""

from typing import TYPE_CHECKING, Any, Dict

from .base import CellBase

if TYPE_CHECKING:
    try:
        from nbformat import NotebookNode
    except ImportError:
        NotebookNode = Dict[str, Any]


class ConvergenceCells(CellBase):
    """Creates convergence analysis cells."""

    def create_convergence_analysis_cell(self) -> "NotebookNode":
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

    def create_advanced_metrics_markdown_cell(self) -> "NotebookNode":
        """Create advanced metrics explanation markdown cell.

        Returns:
            Jupyter notebook markdown cell
        """
        content = """## Advanced Convergence Metrics

The following analysis explores deeper patterns in the conversation dynamics:

- **Vocabulary Convergence**: How agents adopt each other's word choices
- **Structural Mimicry**: Alignment in sentence patterns and message structure  
- **Turn-by-turn Dynamics**: How convergence evolves throughout conversations
- **Cross-conversation Patterns**: Systematic behaviors across multiple runs"""

        return self._make_markdown_cell(content)

    def create_advanced_metrics_code_cell(self) -> "NotebookNode":
        """Create advanced metrics analysis code cell.

        Returns:
            Jupyter notebook code cell
        """
        code = """# Advanced Metrics Analysis
if 'turn_metrics' in locals():
    # Calculate additional metrics
    if 'vocabulary_overlap' in turn_metrics.columns:
        # Convergence velocity (rate of change)
        for conv_id in turn_metrics['conversation_id'].unique():
            mask = turn_metrics['conversation_id'] == conv_id
            turn_metrics.loc[mask, 'convergence_velocity'] = \\
                turn_metrics.loc[mask, 'convergence_score'].diff()
    
    # Statistical summary by conversation
    conv_summary = turn_metrics.groupby('conversation_id').agg({
        'convergence_score': ['mean', 'std', 'min', 'max', 'last'],
        'vocabulary_overlap': ['mean', 'last'] if 'vocabulary_overlap' in turn_metrics.columns else [],
        'message_length_a': ['mean', 'std'] if 'message_length_a' in turn_metrics.columns else [],
        'message_length_b': ['mean', 'std'] if 'message_length_b' in turn_metrics.columns else [],
    })
    
    print("\\n=== Conversation-level Summary Statistics ===")
    print(conv_summary.describe())
    
    # Identify high/low convergence conversations
    if 'convergence_score' in turn_metrics.columns:
        final_convergence = turn_metrics.groupby('conversation_id')['convergence_score'].last()
        high_conv = final_convergence.nlargest(3)
        low_conv = final_convergence.nsmallest(3)
        
        print(f"\\n=== High Convergence Conversations ===")
        for conv_id, score in high_conv.items():
            print(f"  {conv_id}: {score:.3f}")
        
        print(f"\\n=== Low Convergence Conversations ===")
        for conv_id, score in low_conv.items():
            print(f"  {conv_id}: {score:.3f}")"""

        return self._make_code_cell(code)
