# pidgin/cli/tools.py
"""Analysis and utility commands."""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from .helpers import (
    find_conversations,
    format_file_size,
    load_conversation_metadata
)
from .constants import (
    NORD_CYAN, NORD_GREEN, NORD_YELLOW, NORD_RED, NORD_BLUE,
    TRANSCRIPT_PATTERN, EVENTS_PATTERN, STATE_PATTERN
)
from ..analysis import TranscriptAnalyzer, ConvergenceCalculator
from ..io.transcripts import TranscriptManager

console = Console()


@click.command()
@click.argument('conversation_path', required=False)
@click.option('--format', '-f', 
              type=click.Choice(['markdown', 'json', 'text']), 
              default='markdown',
              help='Output format')
@click.option('--output', '-o', help='Save to file instead of printing')
@click.option('--no-timestamps', is_flag=True, help='Hide timestamps')
@click.option('--no-metadata', is_flag=True, help='Hide metadata section')
def transcribe(conversation_path, format, output, no_timestamps, no_metadata):
    """Generate a transcript from conversation files.
    
    If no path is provided, shows recent conversations to choose from.
    
    \b
    EXAMPLES:
        pidgin transcribe
        pidgin transcribe ./pidgin_output/conversations/2024-01-15/143022_abc123
        pidgin transcribe -f json -o transcript.json
    """
    # Find conversation directory
    if not conversation_path:
        conversations = find_conversations()
        if not conversations:
            console.print(f"[{NORD_RED}]No conversations found[/{NORD_RED}]")
            return
        
        # Show selection menu
        console.print(f"\n[bold {NORD_BLUE}]Select a conversation:[/bold {NORD_BLUE}]")
        
        for i, conv_dir in enumerate(conversations[:10], 1):
            metadata = load_conversation_metadata(conv_dir)
            
            # Format display
            date_str = conv_dir.parent.name
            conv_id = conv_dir.name
            
            agents_str = "Unknown agents"
            if metadata.get('agents'):
                agents = metadata['agents']
                if len(agents) >= 2:
                    agents_str = f"{agents[0].get('display_name', '?')} ↔ {agents[1].get('display_name', '?')}"
            
            turns = metadata.get('total_turns', 0)
            size = format_file_size(metadata.get('transcript_size', 0))
            
            console.print(f"  {i}. [{NORD_CYAN}]{date_str}/{conv_id}[/{NORD_CYAN}]")
            console.print(f"     {agents_str} - {turns} turns - {size}")
        
        selection = console.input(f"\n[{NORD_BLUE}]Enter selection (1-10): [/{NORD_BLUE}]")
        
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(conversations[:10]):
                conversation_path = conversations[idx]
            else:
                console.print(f"[{NORD_RED}]Invalid selection[/{NORD_RED}]")
                return
        except ValueError:
            console.print(f"[{NORD_RED}]Invalid selection[/{NORD_RED}]")
            return
    
    conv_dir = Path(conversation_path)
    if not conv_dir.exists():
        console.print(f"[{NORD_RED}]Conversation directory not found: {conversation_path}[/{NORD_RED}]")
        return
    
    # Check for transcript file
    transcript_file = conv_dir / TRANSCRIPT_PATTERN
    if not transcript_file.exists():
        console.print(f"[{NORD_RED}]No transcript found in {conv_dir}[/{NORD_RED}]")
        return
    
    # Read transcript
    with open(transcript_file) as f:
        content = f.read()
    
    # Format based on output type
    if format == 'json':
        # Parse markdown to JSON
        transcript_data = _parse_transcript_to_json(content, conv_dir)
        output_content = json.dumps(transcript_data, indent=2)
    elif format == 'text':
        # Convert to plain text
        output_content = _markdown_to_text(content)
    else:
        # Keep as markdown
        output_content = content
    
    # Apply filters
    if no_timestamps and format == 'markdown':
        # Remove timestamp lines
        lines = output_content.split('\n')
        filtered = [line for line in lines if not line.strip().startswith('*[20')]
        output_content = '\n'.join(filtered)
    
    if no_metadata and format == 'markdown':
        # Remove metadata section
        if '## Conversation' in output_content:
            output_content = output_content[output_content.find('## Conversation'):]
    
    # Output
    if output:
        output_path = Path(output)
        output_path.write_text(output_content)
        console.print(f"[{NORD_GREEN}]✓ Transcript saved to {output_path}[/{NORD_GREEN}]")
    else:
        if format == 'markdown':
            # Pretty print markdown
            from rich.markdown import Markdown
            console.print(Markdown(output_content))
        else:
            console.print(output_content)


@click.command()
@click.argument('path', required=False)
@click.option('--depth', '-d',
              type=click.Choice(['summary', 'detailed', 'full']),
              default='summary',
              help='Analysis depth')
@click.option('--output', '-o', help='Save report to file')
def report(path, depth, output):
    """Generate analysis report for conversations.
    
    Can analyze a single conversation or an entire experiment.
    
    \b
    EXAMPLES:
        pidgin report
        pidgin report ./pidgin_output/conversations/2024-01-15
        pidgin report experiment_abc123 -d detailed
    """
    if not path:
        # Show options
        console.print(f"\n[bold {NORD_BLUE}]What would you like to analyze?[/bold {NORD_BLUE}]")
        console.print("  1. Recent conversation")
        console.print("  2. Specific date")
        console.print("  3. Experiment")
        
        choice = console.input(f"\n[{NORD_BLUE}]Enter selection (1-3): [/{NORD_BLUE}]")
        
        if choice == '1':
            conversations = find_conversations()
            if conversations:
                path = str(conversations[0])
            else:
                console.print(f"[{NORD_RED}]No conversations found[/{NORD_RED}]")
                return
        elif choice == '2':
            date = console.input(f"[{NORD_BLUE}]Enter date (YYYY-MM-DD): [/{NORD_BLUE}]")
            path = f"./pidgin_output/conversations/{date}"
        elif choice == '3':
            from ..experiments import ExperimentStore
            storage = ExperimentStore()
            experiments = storage.list_experiments()
            
            if not experiments:
                console.print(f"[{NORD_RED}]No experiments found[/{NORD_RED}]")
                return
            
            console.print(f"\n[bold {NORD_BLUE}]Recent experiments:[/bold {NORD_BLUE}]")
            for i, exp in enumerate(experiments[:5], 1):
                console.print(f"  {i}. {exp['name']} ({exp['experiment_id']})")
            
            sel = console.input(f"\n[{NORD_BLUE}]Enter selection (1-5): [/{NORD_BLUE}]")
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(experiments[:5]):
                    path = experiments[idx]['experiment_id']
                else:
                    console.print(f"[{NORD_RED}]Invalid selection[/{NORD_RED}]")
                    return
            except ValueError:
                console.print(f"[{NORD_RED}]Invalid selection[/{NORD_RED}]")
                return
        else:
            console.print(f"[{NORD_RED}]Invalid selection[/{NORD_RED}]")
            return
    
    # Generate report based on path type
    report_content = _generate_report(path, depth)
    
    if output:
        output_path = Path(output)
        output_path.write_text(report_content)
        console.print(f"[{NORD_GREEN}]✓ Report saved to {output_path}[/{NORD_GREEN}]")
    else:
        console.print(report_content)


@click.command()
@click.argument('conv1')
@click.argument('conv2')
@click.option('--metric', '-m',
              type=click.Choice(['all', 'convergence', 'vocabulary', 'structure']),
              default='all',
              help='Comparison metric')
def compare(conv1, conv2, metric):
    """Compare two conversations.
    
    Shows differences in convergence patterns, vocabulary evolution,
    and structural characteristics.
    
    \b
    EXAMPLES:
        pidgin compare conv1_path conv2_path
        pidgin compare --metric convergence conv1 conv2
    """
    # Load both conversations
    conv1_data = _load_conversation_data(conv1)
    conv2_data = _load_conversation_data(conv2)
    
    if not conv1_data or not conv2_data:
        console.print(f"[{NORD_RED}]Failed to load conversation data[/{NORD_RED}]")
        return
    
    console.print(f"\n[bold {NORD_BLUE}]◆ Conversation Comparison[/bold {NORD_BLUE}]")
    
    # Basic info
    table = Table(show_header=True)
    table.add_column("Property", style="cyan")
    table.add_column("Conversation 1", style="yellow")
    table.add_column("Conversation 2", style="green")
    
    # Add basic properties
    table.add_row("Agents", 
                  f"{conv1_data['agent_a']} ↔ {conv1_data['agent_b']}", 
                  f"{conv2_data['agent_a']} ↔ {conv2_data['agent_b']}")
    table.add_row("Total Turns", 
                  str(conv1_data['total_turns']), 
                  str(conv2_data['total_turns']))
    table.add_row("Total Words",
                  str(conv1_data['total_words']),
                  str(conv2_data['total_words']))
    
    console.print(table)
    
    # Convergence comparison
    if metric in ['all', 'convergence']:
        console.print(f"\n[{NORD_CYAN}]Convergence Analysis:[/{NORD_CYAN}]")
        
        # Calculate convergence for both
        conv1_scores = conv1_data.get('convergence_scores', [])
        conv2_scores = conv2_data.get('convergence_scores', [])
        
        if conv1_scores and conv2_scores:
            # Average convergence
            avg1 = sum(conv1_scores) / len(conv1_scores)
            avg2 = sum(conv2_scores) / len(conv2_scores)
            
            console.print(f"  Average convergence: {avg1:.3f} vs {avg2:.3f}")
            console.print(f"  Final convergence: {conv1_scores[-1]:.3f} vs {conv2_scores[-1]:.3f}")
            
            # Show trend
            console.print(f"\n  Convergence over time:")
            max_turns = min(len(conv1_scores), len(conv2_scores), 10)
            for i in range(max_turns):
                bar1 = "█" * int(conv1_scores[i] * 20)
                bar2 = "█" * int(conv2_scores[i] * 20)
                console.print(f"  Turn {i+1:2d}: [{NORD_YELLOW}]{bar1:<20}[/{NORD_YELLOW}] [{NORD_GREEN}]{bar2:<20}[/{NORD_GREEN}]")
    
    # Vocabulary comparison
    if metric in ['all', 'vocabulary']:
        console.print(f"\n[{NORD_CYAN}]Vocabulary Analysis:[/{NORD_CYAN}]")
        
        vocab1 = set(conv1_data.get('unique_words', []))
        vocab2 = set(conv2_data.get('unique_words', []))
        
        shared = vocab1 & vocab2
        only1 = vocab1 - vocab2
        only2 = vocab2 - vocab1
        
        console.print(f"  Vocabulary size: {len(vocab1)} vs {len(vocab2)}")
        console.print(f"  Shared words: {len(shared)}")
        console.print(f"  Unique to conv1: {len(only1)}")
        console.print(f"  Unique to conv2: {len(only2)}")
        
        # Show some unique words
        if only1:
            sample1 = list(only1)[:5]
            console.print(f"    Examples: {', '.join(sample1)}")
        if only2:
            sample2 = list(only2)[:5]
            console.print(f"    Examples: {', '.join(sample2)}")
    
    # Structure comparison
    if metric in ['all', 'structure']:
        console.print(f"\n[{NORD_CYAN}]Structural Analysis:[/{NORD_CYAN}]")
        
        console.print(f"  Avg message length: {conv1_data['avg_message_length']:.1f} vs {conv2_data['avg_message_length']:.1f}")
        console.print(f"  Question ratio: {conv1_data['question_ratio']:.2%} vs {conv2_data['question_ratio']:.2%}")
        console.print(f"  Exclamation ratio: {conv1_data['exclamation_ratio']:.2%} vs {conv2_data['exclamation_ratio']:.2%}")


def _parse_transcript_to_json(markdown_content: str, conv_dir: Path) -> dict:
    """Parse markdown transcript to JSON format."""
    result = {
        'metadata': {},
        'messages': []
    }
    
    # Try to load state.json for metadata
    state_file = conv_dir / STATE_PATTERN
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
            result['metadata'] = {
                'conversation_id': state.get('conversation_id'),
                'started_at': state.get('started_at'),
                'agents': state.get('agents', []),
                'initial_prompt': state.get('initial_prompt'),
                'total_turns': state.get('total_turns', 0)
            }
    
    # Parse messages from markdown
    lines = markdown_content.split('\n')
    current_message = None
    
    for line in lines:
        # Check for agent message start
        if line.startswith('### Agent A:') or line.startswith('### Agent B:'):
            if current_message:
                result['messages'].append(current_message)
            
            agent = 'agent_a' if 'Agent A:' in line else 'agent_b'
            current_message = {
                'agent': agent,
                'content': '',
                'timestamp': None
            }
        
        # Check for timestamp
        elif line.strip().startswith('*[20') and current_message:
            # Extract timestamp
            timestamp = line.strip().strip('*[]')
            current_message['timestamp'] = timestamp
        
        # Add content
        elif current_message and line.strip():
            if current_message['content']:
                current_message['content'] += '\n'
            current_message['content'] += line
    
    # Add last message
    if current_message:
        result['messages'].append(current_message)
    
    return result


def _markdown_to_text(markdown_content: str) -> str:
    """Convert markdown to plain text."""
    lines = markdown_content.split('\n')
    text_lines = []
    
    for line in lines:
        # Remove markdown headers
        if line.startswith('#'):
            line = line.lstrip('#').strip()
            text_lines.append(line.upper())
        
        # Remove emphasis
        line = line.replace('**', '').replace('*', '').replace('`', '')
        
        # Remove links
        import re
        line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
        
        text_lines.append(line)
    
    return '\n'.join(text_lines)


def _generate_report(path: str, depth: str) -> str:
    """Generate analysis report for given path."""
    path_obj = Path(path)
    
    # Check if it's an experiment ID
    if path.startswith('exp_'):
        return _generate_experiment_report(path, depth)
    
    # Check if it's a directory
    if path_obj.is_dir():
        if (path_obj / TRANSCRIPT_PATTERN).exists():
            # Single conversation
            return _generate_conversation_report(path_obj, depth)
        else:
            # Multiple conversations (date directory)
            return _generate_batch_report(path_obj, depth)
    
    console.print(f"[{NORD_RED}]Invalid path: {path}[/{NORD_RED}]")
    return ""


def _generate_conversation_report(conv_dir: Path, depth: str) -> str:
    """Generate report for a single conversation."""
    analyzer = TranscriptAnalyzer()
    
    # Load conversation data
    transcript_file = conv_dir / TRANSCRIPT_PATTERN
    events_file = conv_dir / EVENTS_PATTERN
    
    if not transcript_file.exists():
        return f"[{NORD_RED}]No transcript found in {conv_dir}[/{NORD_RED}]"
    
    # Analyze
    analysis = analyzer.analyze_conversation(conv_dir)
    
    # Format report
    report = [f"# Conversation Analysis Report\n"]
    report.append(f"**Path**: {conv_dir}")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Basic metrics
    report.append("## Overview")
    report.append(f"- Total turns: {analysis['total_turns']}")
    report.append(f"- Total messages: {analysis['total_messages']}")
    report.append(f"- Total words: {analysis['total_words']}")
    report.append(f"- Unique words: {analysis['unique_words']}")
    report.append(f"- Average message length: {analysis['avg_message_length']:.1f} words\n")
    
    # Convergence
    if 'convergence_scores' in analysis and analysis['convergence_scores']:
        report.append("## Convergence Analysis")
        scores = analysis['convergence_scores']
        report.append(f"- Initial convergence: {scores[0]:.3f}")
        report.append(f"- Final convergence: {scores[-1]:.3f}")
        report.append(f"- Average convergence: {sum(scores)/len(scores):.3f}")
        report.append(f"- Peak convergence: {max(scores):.3f} (turn {scores.index(max(scores)) + 1})\n")
    
    if depth in ['detailed', 'full']:
        # Vocabulary evolution
        report.append("## Vocabulary Evolution")
        report.append(f"- Words introduced by Agent A: {analysis.get('words_introduced_a', 0)}")
        report.append(f"- Words introduced by Agent B: {analysis.get('words_introduced_b', 0)}")
        report.append(f"- Vocabulary overlap: {analysis.get('vocabulary_overlap', 0):.2%}\n")
    
    if depth == 'full':
        # Turn-by-turn analysis
        report.append("## Turn-by-Turn Metrics")
        # Add detailed metrics here
    
    return '\n'.join(report)


def _generate_batch_report(directory: Path, depth: str) -> str:
    """Generate report for multiple conversations."""
    conversations = find_conversations(str(directory))
    
    if not conversations:
        return f"[{NORD_RED}]No conversations found in {directory}[/{NORD_RED}]"
    
    report = [f"# Batch Analysis Report\n"]
    report.append(f"**Directory**: {directory}")
    report.append(f"**Conversations**: {len(conversations)}")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Analyze each conversation
    total_turns = 0
    total_words = 0
    all_convergence = []
    
    for conv_dir in conversations:
        analyzer = TranscriptAnalyzer()
        analysis = analyzer.analyze_conversation(conv_dir)
        
        total_turns += analysis.get('total_turns', 0)
        total_words += analysis.get('total_words', 0)
        
        if 'convergence_scores' in analysis:
            all_convergence.extend(analysis['convergence_scores'])
    
    # Summary statistics
    report.append("## Summary Statistics")
    report.append(f"- Total turns across all conversations: {total_turns}")
    report.append(f"- Total words: {total_words}")
    report.append(f"- Average turns per conversation: {total_turns / len(conversations):.1f}")
    
    if all_convergence:
        report.append(f"\n## Convergence Patterns")
        report.append(f"- Average convergence: {sum(all_convergence) / len(all_convergence):.3f}")
        report.append(f"- Convergence range: {min(all_convergence):.3f} - {max(all_convergence):.3f}")
    
    return '\n'.join(report)


def _generate_experiment_report(experiment_id: str, depth: str) -> str:
    """Generate report for an experiment."""
    from ..experiments import ExperimentStore
    
    storage = ExperimentStore()
    exp = storage.get_experiment(experiment_id)
    
    if not exp:
        return f"[{NORD_RED}]Experiment {experiment_id} not found[/{NORD_RED}]"
    
    report = [f"# Experiment Analysis Report\n"]
    report.append(f"**Experiment**: {exp['name']} ({experiment_id})")
    report.append(f"**Status**: {exp['status']}")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get metrics
    metrics = storage.get_experiment_metrics(experiment_id)
    
    # Configuration
    config = json.loads(exp['config'])
    report.append("## Configuration")
    report.append(f"- Models: {config['agent_a_model']} ↔ {config['agent_b_model']}")
    report.append(f"- Repetitions: {config['repetitions']}")
    report.append(f"- Max turns: {config['max_turns']}")
    
    if config.get('temperature_a') or config.get('temperature_b'):
        temps = []
        if config.get('temperature_a'):
            temps.append(f"A: {config['temperature_a']}")
        if config.get('temperature_b'):
            temps.append(f"B: {config['temperature_b']}")
        report.append(f"- Temperature: {', '.join(temps)}")
    
    report.append(f"\n## Results")
    report.append(f"- Completed conversations: {exp['completed_conversations']}/{exp['total_conversations']}")
    
    if exp['failed_conversations'] > 0:
        report.append(f"- Failed conversations: {exp['failed_conversations']}")
    
    # Convergence statistics
    conv_stats = metrics.get('convergence_stats', {})
    if conv_stats:
        report.append(f"\n## Convergence Analysis")
        report.append(f"- Average convergence: {conv_stats.get('avg', 0):.3f}")
        report.append(f"- Convergence range: {conv_stats.get('min', 0):.3f} - {conv_stats.get('max', 0):.3f}")
    
    # Vocabulary analysis
    if 'top_words' in metrics and metrics['top_words']:
        report.append(f"\n## Vocabulary Analysis")
        report.append("### Most Common Words:")
        for word, freq in metrics['top_words'][:10]:
            report.append(f"- '{word}': {freq} occurrences")
    
    if 'emergent_words' in metrics and metrics['emergent_words']:
        report.append("\n### Emergent Words (appearing after turn 5):")
        for word, turn in metrics['emergent_words'][:10]:
            report.append(f"- '{word}' first appeared in turn {turn}")
    
    return '\n'.join(report)


def _load_conversation_data(conv_path: str) -> Optional[dict]:
    """Load and analyze conversation data."""
    conv_dir = Path(conv_path)
    
    if not conv_dir.exists() or not conv_dir.is_dir():
        return None
    
    analyzer = TranscriptAnalyzer()
    
    try:
        analysis = analyzer.analyze_conversation(conv_dir)
        
        # Add additional metrics
        transcript_file = conv_dir / TRANSCRIPT_PATTERN
        if transcript_file.exists():
            with open(transcript_file) as f:
                content = f.read()
                
            # Count questions and exclamations
            questions = content.count('?')
            exclamations = content.count('!')
            total_sentences = content.count('.') + questions + exclamations
            
            analysis['question_ratio'] = questions / total_sentences if total_sentences > 0 else 0
            analysis['exclamation_ratio'] = exclamations / total_sentences if total_sentences > 0 else 0
        
        return analysis
    except Exception as e:
        console.print(f"[{NORD_RED}]Error analyzing {conv_path}: {e}[/{NORD_RED}]")
        return None