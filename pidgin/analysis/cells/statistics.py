"""Basic statistics cells for notebooks."""

from typing import TYPE_CHECKING, Any, Dict

from .base import CellBase

if TYPE_CHECKING:
    try:
        from nbformat import NotebookNode
    except ImportError:
        NotebookNode = Dict[str, Any]


class StatisticsCells(CellBase):
    """Creates basic statistics analysis cells."""

    def create_statistics_cell(self) -> "NotebookNode":
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

    def create_length_analysis_cell(self) -> "NotebookNode":
        """Create message length analysis code cell.

        Returns:
            Jupyter notebook code cell
        """
        code = """# Message Length Analysis
if 'turn_metrics' in locals() and 'message_length_a' in turn_metrics.columns:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # 1. Message lengths over time
    ax = axes[0]
    ax.plot(turn_metrics['turn_number'], turn_metrics['message_length_a'], 
            'b-', alpha=0.3, label='Agent A')
    ax.plot(turn_metrics['turn_number'], turn_metrics['message_length_b'],
            'r-', alpha=0.3, label='Agent B')
    
    # Add rolling averages
    window = min(10, len(turn_metrics) // 4)
    if window > 1:
        ax.plot(turn_metrics['turn_number'],
                turn_metrics['message_length_a'].rolling(window, center=True).mean(),
                'b-', linewidth=2, label=f'Agent A (MA-{window})')
        ax.plot(turn_metrics['turn_number'],
                turn_metrics['message_length_b'].rolling(window, center=True).mean(),
                'r-', linewidth=2, label=f'Agent B (MA-{window})')
    
    ax.set_xlabel('Turn Number')
    ax.set_ylabel('Message Length (characters)')
    ax.set_title('Message Length Over Time')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. Length distribution
    ax = axes[1]
    ax.hist([turn_metrics['message_length_a'], turn_metrics['message_length_b']],
            label=['Agent A', 'Agent B'], alpha=0.6, bins=30)
    ax.set_xlabel('Message Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Message Length Distribution')
    ax.legend()
    
    # 3. Length convergence
    ax = axes[2]
    length_diff = abs(turn_metrics['message_length_a'] - turn_metrics['message_length_b'])
    ax.plot(turn_metrics['turn_number'], length_diff, 'g-', alpha=0.5)
    
    # Add trend line
    z = np.polyfit(turn_metrics['turn_number'], length_diff, 1)
    p = np.poly1d(z)
    ax.plot(turn_metrics['turn_number'], p(turn_metrics['turn_number']),
            "r--", linewidth=2, label=f'Trend: {z[0]:.2f}')
    
    ax.set_xlabel('Turn Number')
    ax.set_ylabel('|Length A - Length B|')
    ax.set_title('Message Length Difference')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()"""

        return self._make_code_cell(code)
