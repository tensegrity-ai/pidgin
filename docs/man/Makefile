# Makefile for Pidgin man pages

PREFIX ?= /usr/local
MANDIR = $(PREFIX)/share/man

# Man page files
MAN1 = pidgin.1 pidgin-run.1 pidgin-stop.1 pidgin-monitor.1 pidgin-branch.1 pidgin-info.1
MAN5 = pidgin-yaml.5
MAN7 = pidgin-metrics.7

# Installation directories
MAN1DIR = $(MANDIR)/man1
MAN5DIR = $(MANDIR)/man5
MAN7DIR = $(MANDIR)/man7

.PHONY: all install uninstall clean

all:
	@echo "Run 'make install' to install man pages"
	@echo "Run 'make uninstall' to remove man pages"

install:
	@echo "Installing man pages to $(MANDIR)"
	@mkdir -p $(MAN1DIR) $(MAN5DIR) $(MAN7DIR)
	@for page in $(MAN1); do \
		echo "Installing $$page"; \
		install -m 644 $$page $(MAN1DIR)/; \
	done
	@for page in $(MAN5); do \
		echo "Installing $$page"; \
		install -m 644 $$page $(MAN5DIR)/; \
	done
	@for page in $(MAN7); do \
		echo "Installing $$page"; \
		install -m 644 $$page $(MAN7DIR)/; \
	done
	@echo "Man pages installed successfully"

uninstall:
	@echo "Removing man pages from $(MANDIR)"
	@for page in $(MAN1); do \
		echo "Removing $$page"; \
		rm -f $(MAN1DIR)/$$page; \
	done
	@for page in $(MAN5); do \
		echo "Removing $$page"; \
		rm -f $(MAN5DIR)/$$page; \
	done
	@for page in $(MAN7); do \
		echo "Removing $$page"; \
		rm -f $(MAN7DIR)/$$page; \
	done
	@echo "Man pages removed successfully"

clean:
	@echo "Nothing to clean"

# Development targets
view: $(MAN1) $(MAN5) $(MAN7)
	@echo "Preview man pages with:"
	@echo "  man ./pidgin.1"
	@echo "  man ./pidgin-run.1"
	@echo "  etc."

check:
	@for page in $(MAN1) $(MAN5) $(MAN7); do \
		echo "Checking $$page..."; \
		groff -t -man -Tascii $$page > /dev/null; \
	done
	@echo "All man pages are valid"