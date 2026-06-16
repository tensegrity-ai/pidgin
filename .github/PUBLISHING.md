# Publishing Setup Guide

This document explains how automated publishing to PyPI works.

## PyPI Trusted Publishing

### One-time Setup

1. Go to [PyPI](https://pypi.org) and log in
2. Navigate to: Your projects → pidgin-ai → Settings → Publishing
3. Add a new "pending publisher" with:
   - **Owner**: `tensegrity-ai`
   - **Repository**: `pidgin`
   - **Workflow name**: `publish.yml`
   - **Environment**: `pypi`

4. In GitHub repo settings, create an environment named `pypi`:
   - Settings → Environments → New environment → Name: `pypi`
   - A required-reviewer protection rule is configured so each publish
     waits for manual approval.

### Publishing Process

1. Update version in `pyproject.toml`
2. Commit: `git commit -am "chore: bump version to X.Y.Z"`
3. Create GitHub release with tag `vX.Y.Z`
4. `publish.yml` builds and publishes to PyPI (after approval)

## Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md (if maintained)
- [ ] Commit version bump
- [ ] Create GitHub release with tag `vX.Y.Z`
- [ ] Approve the `pypi` environment deployment
- [ ] Verify PyPI publish succeeded
- [ ] Test: `uv tool install pidgin-ai` (or `pip install pidgin-ai==X.Y.Z`)
