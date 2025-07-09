"""Tests for context_utils module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from pidgin.providers.context_utils import (
    apply_context_truncation,
    split_system_and_conversation_messages
)
from pidgin.core.types import Message


class TestContextUtils:
    """Test suite for context utility functions."""
    
    def test_apply_context_truncation_no_truncation(self):
        """Test when messages are under the limit."""
        messages = [
            Message(role="system", content="You are a helpful assistant.", agent_id="system"),
            Message(role="user", content="Hello", agent_id="agent_a"),
            Message(role="assistant", content="Hi there!", agent_id="agent_b")
        ]
        
        with patch('pidgin.providers.context_utils.ProviderContextManager') as mock_manager:
            mock_instance = Mock()
            mock_instance.prepare_context.return_value = messages
            mock_manager.return_value = mock_instance
            
            result = apply_context_truncation(messages, "anthropic", "claude-3")
            
            assert result == messages
            mock_instance.prepare_context.assert_called_once_with(
                messages,
                provider="anthropic",
                model="claude-3",
                event_bus=None,
                conversation_id=None,
                agent_id=None,
                turn_number=None
            )
    
    def test_apply_context_truncation_with_truncation(self):
        """Test when messages are truncated."""
        original_messages = [
            Message(role="system", content="System prompt", agent_id="system"),
            Message(role="user", content="Message 1", agent_id="agent_a"),
            Message(role="assistant", content="Response 1", agent_id="agent_b"),
            Message(role="user", content="Message 2", agent_id="agent_a"),
            Message(role="assistant", content="Response 2", agent_id="agent_b"),
        ]
        
        truncated_messages = original_messages[:3]  # Only first 3 messages
        
        with patch('pidgin.providers.context_utils.ProviderContextManager') as mock_manager:
            mock_instance = Mock()
            mock_instance.prepare_context.return_value = truncated_messages
            mock_manager.return_value = mock_instance
            
            with patch('pidgin.providers.context_utils.logger') as mock_logger:
                result = apply_context_truncation(
                    original_messages, 
                    "openai", 
                    "gpt-4"
                )
                
                assert result == truncated_messages
                mock_logger.info.assert_called_once()
                log_message = mock_logger.info.call_args[0][0]
                assert "Truncated from 5 to 3 messages" in log_message
                assert "gpt-4" in log_message
    
    def test_apply_context_truncation_with_custom_logger(self):
        """Test using a custom logger name."""
        messages = [Message(role="user", content="Test", agent_id="agent_a")]
        
        with patch('pidgin.providers.context_utils.ProviderContextManager') as mock_manager:
            mock_instance = Mock()
            mock_instance.prepare_context.return_value = messages
            mock_manager.return_value = mock_instance
            
            with patch('pidgin.providers.context_utils.logging.getLogger') as mock_get_logger:
                mock_custom_logger = Mock()
                mock_get_logger.return_value = mock_custom_logger
                
                result = apply_context_truncation(
                    messages,
                    "google",
                    logger_name="custom.logger"
                )
                
                mock_get_logger.assert_called_once_with("custom.logger")
    
    def test_split_system_and_conversation_messages(self):
        """Test splitting messages by role."""
        messages = [
            Message(role="system", content="System message 1", agent_id="system"),
            Message(role="system", content="System message 2", agent_id="system"),
            Message(role="user", content="User message", agent_id="agent_a"),
            Message(role="assistant", content="Assistant message", agent_id="agent_b"),
            Message(role="user", content="Another user message", agent_id="agent_a"),
        ]
        
        system_msgs, conv_msgs = split_system_and_conversation_messages(messages)
        
        assert system_msgs == ["System message 1", "System message 2"]
        assert conv_msgs == [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant message"},
            {"role": "user", "content": "Another user message"},
        ]
    
    def test_split_system_and_conversation_messages_no_system(self):
        """Test splitting when there are no system messages."""
        messages = [
            Message(role="user", content="User message", agent_id="agent_a"),
            Message(role="assistant", content="Assistant message", agent_id="agent_b"),
        ]
        
        system_msgs, conv_msgs = split_system_and_conversation_messages(messages)
        
        assert system_msgs == []
        assert conv_msgs == [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant message"},
        ]
    
    def test_split_system_and_conversation_messages_only_system(self):
        """Test splitting when there are only system messages."""
        messages = [
            Message(role="system", content="System message 1", agent_id="system"),
            Message(role="system", content="System message 2", agent_id="system"),
        ]
        
        system_msgs, conv_msgs = split_system_and_conversation_messages(messages)
        
        assert system_msgs == ["System message 1", "System message 2"]
        assert conv_msgs == []
    
    def test_split_system_and_conversation_messages_empty(self):
        """Test splitting empty message list."""
        system_msgs, conv_msgs = split_system_and_conversation_messages([])
        
        assert system_msgs == []
        assert conv_msgs == []