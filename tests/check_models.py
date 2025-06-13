#!/usr/bin/env python3
"""Test script to verify model availability without incurring costs."""

import asyncio
import os
from pidgin.models import MODELS
from pidgin.providers.anthropic import AnthropicProvider
from pidgin.providers.openai import OpenAIProvider
from pidgin.types import Message

async def test_model(provider_class, model_id):
    """Test if a model is available by making a minimal API call."""
    try:
        provider = provider_class(model_id)
        # Create a minimal message to test
        messages = [Message(role="user", content="Hi")]
        response = await provider.get_response(messages)
        return True, "Available"
    except Exception as e:
        error_msg = str(e)
        if "model not found" in error_msg.lower() or "invalid model" in error_msg.lower():
            return False, "Model not found"
        elif "api key" in error_msg.lower():
            return None, "API key missing"
        else:
            return False, f"Error: {error_msg[:50]}..."

async def main():
    """Test all models for availability."""
    print("Testing model availability...\n")
    
    # Check API keys
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not anthropic_key:
        print("⚠️  ANTHROPIC_API_KEY not set - skipping Anthropic models\n")
    if not openai_key:
        print("⚠️  OPENAI_API_KEY not set - skipping OpenAI models\n")
    
    # Test each model
    results = {}
    for model_id, config in MODELS.items():
        if config.provider == "anthropic" and anthropic_key:
            available, msg = await test_model(AnthropicProvider, model_id)
            results[model_id] = (available, msg)
        elif config.provider == "openai" and openai_key:
            available, msg = await test_model(OpenAIProvider, model_id)
            results[model_id] = (available, msg)
    
    # Display results
    print("\nModel Availability Results:")
    print("-" * 60)
    
    for provider in ["anthropic", "openai"]:
        print(f"\n{provider.upper()}:")
        provider_models = [(k, v) for k, v in results.items() 
                          if MODELS[k].provider == provider]
        
        for model_id, (available, msg) in provider_models:
            if available is True:
                status = "✅"
            elif available is False:
                status = "❌"
            else:
                status = "⚠️ "
            
            print(f"  {status} {model_id:<35} {msg}")
    
    print("\nNote: This test makes minimal API calls to verify availability.")
    print("Some models may require specific API access or permissions.")

if __name__ == "__main__":
    asyncio.run(main())