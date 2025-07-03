"""Demo script showing DuckDB advanced features in Pidgin."""

import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from pidgin.database.storage import AsyncExperimentStore
from pidgin.database.async_duckdb import AsyncDuckDB

console = Console()


async def demo_analytics():
    """Demonstrate DuckDB analytics capabilities."""
    # Use test database
    db_path = Path("pidgin_output/experiments/demo.duckdb")
    storage = AsyncExperimentStore(db_path)
    
    try:
        # Initialize database
        await storage.initialize()
        
        console.print(Panel.fit(
            "[bold cyan]DuckDB Analytics Demo[/bold cyan]\n\n"
            "Showcasing advanced DuckDB features:\n"
            "• Native types (STRUCT, MAP)\n"
            "• Analytics views\n"
            "• Time-series analysis\n"
            "• Direct file queries",
            title="Demo"
        ))
        
        # Create sample experiment
        exp_id = await storage.create_experiment(
            "DuckDB Demo",
            {
                'repetitions': 3,
                'max_turns': 10,
                'initial_prompt': 'Discuss technology',
                'temperature_a': 0.7,
                'temperature_b': 0.8
            }
        )
        
        console.print(f"\n[green]Created experiment: {exp_id}[/green]")
        
        # Create sample conversations
        for i in range(3):
            conv_id = f"demo_conv_{i}"
            await storage.create_conversation(exp_id, conv_id, {
                'agent_a_model': 'claude-3-opus',
                'agent_b_model': 'gpt-4',
                'temperature_a': 0.7 + i * 0.1,
                'temperature_b': 0.8
            })
            
            # Log some sample metrics
            for turn in range(5):
                # Simulate word frequencies using MAP type
                word_freq_a = {
                    'hello': 2 + turn,
                    'world': 1 + turn,
                    'technology': 3,
                    'future': turn + 1
                }
                word_freq_b = {
                    'greetings': 1,
                    'world': 2 + turn,
                    'innovation': 2,
                    'future': turn + 2
                }
                
                await storage.log_turn_metrics(
                    conv_id, turn,
                    metrics={
                        'convergence_score': 0.3 + turn * 0.1 + i * 0.05,
                        'vocabulary_overlap': 0.2 + turn * 0.05,
                        'structural_similarity': 0.4 + turn * 0.08,
                        'topic_similarity': 0.5 + turn * 0.06,
                        'style_match': 0.35 + turn * 0.07
                    },
                    word_frequencies={
                        'agent_a': word_freq_a,
                        'agent_b': word_freq_b,
                        'shared': {'world': 3 + turn * 2, 'future': turn + 3}
                    },
                    message_metrics={
                        'agent_a': {
                            'length': 100 + turn * 20,
                            'word_count': 20 + turn * 4,
                            'unique_words': 15 + turn * 2,
                            'type_token_ratio': 0.75 - turn * 0.05,
                            'avg_word_length': 4.5 + turn * 0.1
                        },
                        'agent_b': {
                            'length': 120 + turn * 15,
                            'word_count': 25 + turn * 3,
                            'unique_words': 18 + turn * 2,
                            'type_token_ratio': 0.72 - turn * 0.04,
                            'avg_word_length': 4.8 + turn * 0.1
                        }
                    },
                    timing={
                        'duration_ms': 2000 + turn * 500
                    }
                )
            
            await storage.update_conversation_status(
                conv_id, 'completed',
                convergence_reason='demo_complete',
                final_convergence_score=0.7 + i * 0.05
            )
        
        # Now demonstrate analytics queries
        console.print("\n[bold cyan]Running Analytics Queries[/bold cyan]\n")
        
        # Direct SQL queries using DuckDB features
        db = storage.db
        
        # 1. Query using STRUCT fields
        console.print("[yellow]1. Querying STRUCT fields:[/yellow]")
        result = await db.fetch_all("""
            SELECT 
                conversation_id,
                agents.a.model as agent_a_model,
                agents.b.model as agent_b_model,
                final_metrics.convergence_score
            FROM conversations
            WHERE experiment_id = ?
        """, (exp_id,))
        
        table = Table(title="Conversation Summary")
        table.add_column("Conversation", style="cyan")
        table.add_column("Agent A", style="green")
        table.add_column("Agent B", style="blue")
        table.add_column("Final Convergence", style="yellow")
        
        for row in result:
            table.add_row(
                row['conversation_id'],
                row['agent_a_model'],
                row['agent_b_model'],
                f"{row['convergence_score']:.3f}" if row['convergence_score'] else "N/A"
            )
        
        console.print(table)
        
        # 2. Query MAP type for word frequencies
        console.print("\n[yellow]2. Analyzing word frequencies with MAP type:[/yellow]")
        result = await db.fetch_all("""
            SELECT 
                turn_number,
                cardinality(vocabulary.shared) as shared_vocab_size,
                map_keys(vocabulary.shared) as shared_words
            FROM turn_metrics
            WHERE conversation_id = ?
            ORDER BY turn_number
        """, ('demo_conv_0',))
        
        table = Table(title="Vocabulary Evolution")
        table.add_column("Turn", style="cyan")
        table.add_column("Shared Vocab Size", style="green")
        table.add_column("Shared Words", style="blue")
        
        for row in result:
            words = ", ".join(row['shared_words'][:5])  # Show first 5
            if len(row['shared_words']) > 5:
                words += "..."
            table.add_row(
                str(row['turn_number']),
                str(row['shared_vocab_size']),
                words
            )
        
        console.print(table)
        
        # 3. Time-series analysis with window functions
        console.print("\n[yellow]3. Time-series convergence analysis:[/yellow]")
        result = await db.fetch_all("""
            SELECT 
                turn_number,
                convergence.score as current_score,
                AVG(convergence.score) OVER (
                    ORDER BY turn_number 
                    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                ) as rolling_avg_3,
                convergence.score - LAG(convergence.score, 1) OVER (
                    ORDER BY turn_number
                ) as delta
            FROM turn_metrics
            WHERE conversation_id = ?
            ORDER BY turn_number
        """, ('demo_conv_0',))
        
        table = Table(title="Convergence Trends")
        table.add_column("Turn", style="cyan")
        table.add_column("Score", style="green")
        table.add_column("3-Turn Avg", style="blue")
        table.add_column("Delta", style="yellow")
        
        for row in result:
            delta_str = f"{row['delta']:+.3f}" if row['delta'] is not None else "N/A"
            table.add_row(
                str(row['turn_number']),
                f"{row['current_score']:.3f}",
                f"{row['rolling_avg_3']:.3f}",
                delta_str
            )
        
        console.print(table)
        
        # 4. Aggregate analytics across experiment
        console.print("\n[yellow]4. Experiment-wide analytics:[/yellow]")
        result = await db.fetch_one("""
            SELECT 
                COUNT(DISTINCT c.conversation_id) as total_convs,
                AVG(c.final_metrics.convergence_score) as avg_convergence,
                STDDEV(c.final_metrics.convergence_score) as stddev_convergence,
                MIN(c.final_metrics.convergence_score) as min_convergence,
                MAX(c.final_metrics.convergence_score) as max_convergence,
                SUM(tm.messages.agent_a.word_count + tm.messages.agent_b.word_count) as total_words
            FROM conversations c
            JOIN turn_metrics tm ON c.conversation_id = tm.conversation_id
            WHERE c.experiment_id = ?
        """, (exp_id,))
        
        console.print(Panel.fit(
            f"[bold]Experiment Statistics[/bold]\n\n"
            f"Total Conversations: {result['total_convs']}\n"
            f"Average Convergence: {result['avg_convergence']:.3f}\n"
            f"Std Dev: {result['stddev_convergence']:.3f}\n"
            f"Range: {result['min_convergence']:.3f} - {result['max_convergence']:.3f}\n"
            f"Total Words: {result['total_words']:,}",
            title="Summary"
        ))
        
        # 5. Direct file queries (simulated)
        console.print("\n[yellow]5. Direct file query capability:[/yellow]")
        console.print("""
        [dim]DuckDB can query external files directly:
        
        SELECT * FROM read_json_auto('events_*.jsonl')
        WHERE event_type = 'ConversationEndEvent'
        
        SELECT * FROM read_parquet('archive/*.parquet')
        WHERE experiment_id = ?[/dim]
        """)
        
        # Event sourcing demonstration
        console.print("\n[bold cyan]Event Sourcing[/bold cyan]\n")
        
        # Query events
        events = await storage.get_events(experiment_id=exp_id)
        console.print(f"Total events recorded: {len(events)}")
        
        # Show event types
        event_types = {}
        for event in events:
            event_type = event['event_type']
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        table = Table(title="Event Distribution")
        table.add_column("Event Type", style="cyan")
        table.add_column("Count", style="green")
        
        for event_type, count in sorted(event_types.items()):
            table.add_row(event_type, str(count))
        
        console.print(table)
        
    finally:
        await storage.close()
        console.print("\n[green]Demo complete![/green]")


if __name__ == "__main__":
    asyncio.run(demo_analytics())