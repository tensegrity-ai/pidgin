# Pidgin Manual Pages

This directory contains manual pages for the Pidgin AI conversation research tool.

## Contents

### Section 1 - User Commands
- `pidgin.1` - Main command overview
- `pidgin-run.1` - Run conversations between AI agents
- `pidgin-stop.1` - Stop running experiments
- `pidgin-monitor.1` - System-wide health monitor
- `pidgin-branch.1` - Branch from existing conversations
- `pidgin-info.1` - Display information commands

### Section 5 - File Formats
- `pidgin-yaml.5` - YAML specification format

### Section 7 - Miscellaneous
- `pidgin-metrics.7` - Metrics explanation and formulas

## Installation

### System-wide Installation
```bash
sudo make install
```

### User Installation
```bash
make install PREFIX=$HOME/.local
```

### macOS with Homebrew
If Pidgin is installed via Homebrew, man pages will be installed automatically.

## Viewing Man Pages

After installation:
```bash
man pidgin
man pidgin-run
man pidgin-yaml
# etc.
```

During development (without installation):
```bash
man ./pidgin.1
man ./pidgin-run.1
# etc.
```

## Validation

Check that all man pages are valid:
```bash
make check
```

## Uninstallation

```bash
sudo make uninstall
```

## Format Notes

Man pages use traditional troff/groff formatting:
- `.TH` - Title header
- `.SH` - Section header
- `.TP` - Tagged paragraph
- `.B` - Bold text
- `.I` - Italic text
- `.BR` - Bold-roman alternating
- `.RS`/`.RE` - Relative indent start/end

## Contributing

When adding new commands or features:
1. Update the relevant man page
2. Run `make check` to validate formatting
3. Test viewing with `man ./page-name.X`
4. Include man page updates in your PR