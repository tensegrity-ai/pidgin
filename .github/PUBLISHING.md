# Publishing Setup Guide

This document explains how to set up automated publishing to PyPI and Homebrew.

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
   - Optionally add protection rules (require approval, etc.)

### Publishing Process

1. Update version in `pyproject.toml`
2. Commit: `git commit -am "chore: bump version to X.Y.Z"`
3. Create GitHub release with tag `vX.Y.Z`
4. Workflow automatically publishes to PyPI

## Homebrew Tap

### One-time Setup

1. Create repository: `tensegrity-ai/homebrew-pidgin`

2. Copy contents from `.github/homebrew-tap-template/` to the new repo:
   ```
   homebrew-pidgin/
   ├── Formula/
   │   └── pidgin.rb
   ├── .github/
   │   └── workflows/
   │       └── update-formula.yml
   └── README.md
   ```

3. Create a Personal Access Token (PAT) with `repo` scope:
   - GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
   - Repository access: Only select repositories → `homebrew-pidgin`
   - Permissions: Contents (Read and write)

4. Add the PAT as a secret in the main pidgin repo:
   - Settings → Secrets → Actions → New repository secret
   - Name: `HOMEBREW_TAP_TOKEN`
   - Value: (paste the PAT)

### How It Works

1. When you create a GitHub release, `publish.yml` runs
2. After PyPI publish succeeds, it triggers the homebrew tap update
3. The tap repo's workflow fetches the new version from PyPI
4. Formula is automatically updated with new URL and SHA256

### Manual Formula Update (if needed)

```bash
# Get SHA256 of the PyPI package
curl -sL https://files.pythonhosted.org/packages/source/p/pidgin-ai/pidgin_ai-X.Y.Z.tar.gz | sha256sum
```

## Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md (if maintained)
- [ ] Commit version bump
- [ ] Create GitHub release with tag `vX.Y.Z`
- [ ] Verify PyPI publish succeeded
- [ ] Verify Homebrew formula updated
- [ ] Test: `pip install pidgin-ai==X.Y.Z`
- [ ] Test: `brew upgrade pidgin` (after tap update)
