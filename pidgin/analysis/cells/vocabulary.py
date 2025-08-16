"""Vocabulary analysis cells for notebooks."""

from typing import TYPE_CHECKING, Any, Dict

from .base import CellBase

if TYPE_CHECKING:
    try:
        from nbformat import NotebookNode
    except ImportError:
        NotebookNode = Dict[str, Any]


class VocabularyCells(CellBase):
    """Creates vocabulary analysis cells."""

    def create_vocabulary_analysis_cell(self) -> "NotebookNode":
        """Create vocabulary overlap analysis code cell.

        Returns:
            Jupyter notebook code cell
        """
        code = """# Vocabulary Analysis
if 'turn_metrics' in locals() and 'vocabulary_overlap' in turn_metrics.columns:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # 1. Vocabulary overlap over turns
    ax = axes[0, 0]
    for conv_id in turn_metrics['conversation_id'].unique()[:5]:
        conv_data = turn_metrics[turn_metrics['conversation_id'] == conv_id]
        ax.plot(conv_data['turn_number'], conv_data['vocabulary_overlap'],
                alpha=0.6, linewidth=1.5)
    ax.set_xlabel('Turn Number')
    ax.set_ylabel('Vocabulary Overlap')
    ax.set_title('Vocabulary Overlap Trajectories (First 5 Conversations)')
    ax.grid(True, alpha=0.3)
    
    # 2. Average vocabulary metrics
    ax = axes[0, 1]
    vocab_cols = [col for col in turn_metrics.columns if 'vocab' in col.lower()]
    if vocab_cols:
        avg_vocab = turn_metrics.groupby('turn_number')[vocab_cols].mean()
        for col in vocab_cols:
            ax.plot(avg_vocab.index, avg_vocab[col], label=col, linewidth=2)
        ax.set_xlabel('Turn Number')
        ax.set_ylabel('Score')
        ax.set_title('Average Vocabulary Metrics Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    # 3. Vocabulary overlap distribution
    ax = axes[1, 0]
    ax.hist(turn_metrics['vocabulary_overlap'], bins=30, alpha=0.7,
            color='purple', edgecolor='black')
    ax.axvline(turn_metrics['vocabulary_overlap'].mean(), color='red',
               linestyle='--', label=f"Mean: {turn_metrics['vocabulary_overlap'].mean():.3f}")
    ax.set_xlabel('Vocabulary Overlap')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Vocabulary Overlap Scores')
    ax.legend()
    
    # 4. Correlation with convergence
    ax = axes[1, 1]
    if 'convergence_score' in turn_metrics.columns:
        ax.scatter(turn_metrics['vocabulary_overlap'], 
                   turn_metrics['convergence_score'],
                   alpha=0.3, s=20)
        
        # Add trend line
        z = np.polyfit(turn_metrics['vocabulary_overlap'], 
                       turn_metrics['convergence_score'], 1)
        p = np.poly1d(z)
        x_line = np.linspace(turn_metrics['vocabulary_overlap'].min(),
                            turn_metrics['vocabulary_overlap'].max(), 100)
        ax.plot(x_line, p(x_line), "r-", linewidth=2,
                label=f'Correlation: {np.corrcoef(turn_metrics["vocabulary_overlap"], turn_metrics["convergence_score"])[0,1]:.3f}')
        
        ax.set_xlabel('Vocabulary Overlap')
        ax.set_ylabel('Convergence Score')
        ax.set_title('Vocabulary Overlap vs Convergence')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()"""

        return self._make_code_cell(code)
