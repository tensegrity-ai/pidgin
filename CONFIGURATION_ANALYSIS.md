# Configuration and Environment Handling Analysis

## Summary

After examining the Pidgin codebase's configuration and environment handling, I've identified several issues and areas for improvement. The system uses a mix of YAML configuration files, environment variables, and hardcoded defaults.

## Findings

### 1. Environment Variables

#### API Keys (Required)
- `ANTHROPIC_API_KEY` - Required for Anthropic provider
- `OPENAI_API_KEY` - Required for OpenAI provider  
- `GOOGLE_API_KEY` - Required for Google provider
- `XAI_API_KEY` - Required for xAI provider

#### Internal Environment Variables
- `PIDGIN_ORIGINAL_CWD` - Set at startup to preserve working directory
- `PIDGIN_PROJECT_BASE` - Set by daemon launcher
- `PIDGIN_DEBUG` - Enables debug output in paths.py
- `PIDGIN_QUIET` - Suppresses banner display
- `FORCE_COLOR` / `CLICOLOR_FORCE` - Forces color output

### 2. Configuration Issues Found

#### Missing Environment Variable Validation
- **Issue**: API keys are only validated when provider is instantiated, not at startup
- **Impact**: User gets error only when trying to use a provider
- **Fix**: Add upfront validation for required API keys based on requested models

#### Hardcoded Values That Should Be Configurable
1. **Ollama Server Configuration**
   - Hardcoded to `localhost:11434` in `pidgin/providers/ollama.py`
   - Should support `OLLAMA_HOST` environment variable
   
2. **Rate Limit Defaults**
   - Hardcoded in multiple places (rate_limiter.py, config.py)
   - Should be centralized and overridable via config

3. **Database Lock Timeout**
   - No configurable timeout for DuckDB operations
   - Should have `PIDGIN_DB_TIMEOUT` or config option

4. **Output Directory**
   - Fixed to `pidgin_output/` relative to working directory
   - Should support `PIDGIN_OUTPUT_DIR` environment variable

#### Configuration Inconsistencies
1. **Rate Limits Defined in Multiple Places**
   - `pidgin/core/rate_limiter.py`: DEFAULT_RATE_LIMITS
   - `pidgin/config/config.py`: providers.rate_limiting.custom_limits
   - Should have single source of truth

2. **Token Estimation Multipliers**
   - Different values in config (1.1) vs code (various)
   - Should be consistent and configurable per provider

#### Security Issues
1. **API Keys in Plain Text**
   - No support for encrypted storage or key vaults
   - API keys logged in debug mode (potential leak)
   
2. **No API Key Format Validation**
   - Keys are checked for existence but not format
   - Should validate key patterns to catch typos early

#### Missing Configuration Options
1. **Notification Settings**
   - Desktop notifications are always enabled
   - Should have config option to disable

2. **Logging Configuration**
   - No way to configure log levels or outputs
   - Should support `PIDGIN_LOG_LEVEL` and log file configuration

3. **Provider-Specific Timeouts**
   - No way to configure API timeouts per provider
   - Should support provider-specific timeout configuration

4. **Proxy Configuration**
   - No support for HTTP/HTTPS proxies
   - Should support standard proxy environment variables

#### Default Values That Don't Make Sense
1. **Context Reserve Ratio (0.25)**
   - Too conservative for most use cases
   - Should be 0.1-0.15 for better token utilization

2. **Convergence Threshold (0.85)**
   - Too aggressive for initial exploration
   - Should default to None (disabled) or 0.95

3. **Max Turns Default (20)**
   - Too low for meaningful conversations
   - Should be 50-100 or None (unlimited)

#### Environment Variable Naming Conflicts
- `PWD` is used but can conflict with shell PWD
- Should use `PIDGIN_PWD` or avoid entirely

#### Missing Configuration Documentation
1. **No Documentation for:**
   - Available environment variables
   - Configuration file format
   - Provider override options
   - Rate limit customization

2. **No Example Configuration File**
   - Users have to guess structure from code
   - Should provide `pidgin.example.yaml`

## Recommendations

### Immediate Fixes Needed

1. **Add Environment Variable Validation**
```python
def validate_environment():
    """Validate required environment variables on startup."""
    required_keys = {
        'anthropic': 'ANTHROPIC_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'google': 'GOOGLE_API_KEY',
        'xai': 'XAI_API_KEY'
    }
    # Check only for providers that will be used
```

2. **Make Ollama Host Configurable**
```python
ollama_host = os.getenv('OLLAMA_HOST', 'localhost')
ollama_port = int(os.getenv('OLLAMA_PORT', '11434'))
```

3. **Add Output Directory Configuration**
```python
output_dir = os.getenv('PIDGIN_OUTPUT_DIR', './pidgin_output')
```

4. **Centralize Rate Limit Configuration**
- Move all rate limits to config.py
- Support environment variable overrides
- Document rate limit structure

5. **Add Configuration Documentation**
- Create comprehensive ENV_VARS.md
- Add pidgin.example.yaml
- Document all configuration options

### Security Improvements

1. **Add API Key Validation**
```python
def validate_api_key_format(provider: str, key: str) -> bool:
    """Validate API key format for provider."""
    patterns = {
        'anthropic': r'^sk-ant-[a-zA-Z0-9-_]+$',
        'openai': r'^sk-[a-zA-Z0-9]+$',
        # etc
    }
```

2. **Mask API Keys in Logs**
- Never log full API keys
- Show only first/last 4 characters when needed

3. **Support Secure Key Storage**
- Add support for keyring/keychain
- Document secure key management practices

### Configuration File Improvements

1. **Add Schema Validation**
- Use JSON Schema or similar for YAML validation
- Provide clear error messages for invalid configs

2. **Support Config Inheritance**
- Allow base configs with overrides
- Support environment-specific configs

3. **Add Config Migration**
- Handle config format changes gracefully
- Provide migration tools for updates