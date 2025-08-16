"""Visualization cells for notebooks."""

from typing import TYPE_CHECKING, Any, Dict

from .base import CellBase

if TYPE_CHECKING:
    try:
        from nbformat import NotebookNode
    except ImportError:
        NotebookNode = Dict[str, Any]


class VisualizationCells(CellBase):
    """Creates visualization and turn analysis cells."""

    def create_turn_visualization_cell(self) -> "NotebookNode":
        """Create turn-by-turn visualization code cell.

        Returns:
            Jupyter notebook code cell
        """
        code = """# Turn-by-Turn Visualization
if 'turn_metrics' in locals() and len(turn_metrics) > 0:
    # Select metrics to visualize
    metric_cols = ['convergence_score', 'vocabulary_overlap', 'structural_similarity',
                   'mutual_mimicry', 'message_length_a', 'message_length_b']
    available_metrics = [col for col in metric_cols if col in turn_metrics.columns]
    
    if available_metrics:
        # Create subplot for each metric
        n_metrics = len(available_metrics)
        fig, axes = plt.subplots(n_metrics, 1, figsize=(15, 4*n_metrics))
        
        if n_metrics == 1:
            axes = [axes]
        
        for idx, metric in enumerate(available_metrics):
            ax = axes[idx]
            
            # Plot individual conversations
            for conv_id in turn_metrics['conversation_id'].unique()[:3]:
                conv_data = turn_metrics[turn_metrics['conversation_id'] == conv_id]
                ax.plot(conv_data['turn_number'], conv_data[metric],
                        alpha=0.4, linewidth=1)
            
            # Plot average
            avg_metric = turn_metrics.groupby('turn_number')[metric].mean()
            ax.plot(avg_metric.index, avg_metric.values, 'k-',
                    linewidth=2, label='Average')
            
            ax.set_xlabel('Turn Number')
            ax.set_ylabel(metric.replace('_', ' ').title())
            ax.set_title(f'{metric.replace("_", " ").title()} Over Turns')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        # Create heatmap of correlations
        if len(available_metrics) > 1:
            fig, ax = plt.subplots(figsize=(10, 8))
            correlation_matrix = turn_metrics[available_metrics].corr()
            
            im = ax.imshow(correlation_matrix, cmap='coolwarm', vmin=-1, vmax=1)
            
            # Add colorbar
            plt.colorbar(im, ax=ax)
            
            # Set ticks and labels
            ax.set_xticks(np.arange(len(available_metrics)))
            ax.set_yticks(np.arange(len(available_metrics)))
            ax.set_xticklabels([m.replace('_', ' ').title() for m in available_metrics])
            ax.set_yticklabels([m.replace('_', ' ').title() for m in available_metrics])
            
            # Rotate the tick labels for better fit
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
                     rotation_mode="anchor")
            
            # Add correlation values
            for i in range(len(available_metrics)):
                for j in range(len(available_metrics)):
                    text = ax.text(j, i, f'{correlation_matrix.iloc[i, j]:.2f}',
                                   ha="center", va="center", color="black" if abs(correlation_matrix.iloc[i, j]) < 0.5 else "white")
            
            ax.set_title('Metric Correlations')
            plt.tight_layout()
            plt.show()"""

        return self._make_code_cell(code)
