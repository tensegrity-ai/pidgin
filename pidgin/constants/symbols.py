"""Symbol constants and patterns for analysis."""

# Unicode symbol sets
ARROWS = {'→', '←', '↔', '⇒', '⇐', '⇔', '➜', '➡', '⬅', '↑', '↓', '⬆', '⬇', '↖', '↗', '↘', '↙'}
MATH_SYMBOLS = {'≈', '≡', '≠', '≤', '≥', '±', '×', '÷', '∞', '∑', '∏', '∂', '∇', '√', '∫', '∈', '∉', '∀', '∃', '∅', '^', '+', '=', '<', '>', '*', '/', '%', '-'}
BOX_DRAWING = {'┌', '┐', '└', '┘', '─', '│', '├', '┤', '┬', '┴', '┼', '═', '║', '╔', '╗', '╚', '╝'}
BULLETS = {'•', '◦', '▪', '▫', '■', '□', '▲', '△', '▼', '▽', '◆', '◇', '○', '●', '★', '☆'}

# Combine all special symbols
ALL_SPECIAL_SYMBOLS = ARROWS | MATH_SYMBOLS | BOX_DRAWING | BULLETS

# Emoji unicode ranges for regex patterns
EMOJI_RANGES = [
    (0x1F600, 0x1F64F),  # emoticons
    (0x1F300, 0x1F5FF),  # symbols & pictographs
    (0x1F680, 0x1F6FF),  # transport & map symbols
    (0x1F1E0, 0x1F1FF),  # flags
    (0x2702, 0x27B0),    # dingbats
    (0x24C2, 0x1F251),   # enclosed characters
    (0x1F900, 0x1F9FF),  # supplemental symbols and pictographs
    (0x2600, 0x26FF),    # miscellaneous symbols
]

# ASCII arrow patterns
ASCII_ARROWS = ['<-', '->', '<->', '=>', '<=', '<=>']

# Common separators
SEPARATORS = {
    # Horizontal lines
    '─' * 10, '━' * 10, '═' * 10, '-' * 10, '_' * 10, '=' * 10,
    # Dots
    '·' * 10, '•' * 10, '.' * 10,
    # Mixed
    '+-' * 5, '*-' * 5, '=-' * 5,
}