/**
 * Main chat interface component - Claude.ai inspired UI
 */
import React, { useState, useRef, useEffect } from 'react';
import { apiClient } from '../api/client';
import { ChatMessage as ChatMessageType, StoredMessage } from '../types/api';
import ChatMessage from './ChatMessage';

interface ChatInterfaceProps {
  sessionId: string;
  taskType: 'reasoning' | 'coding';
  initialMessages?: StoredMessage[];
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ sessionId, taskType, initialMessages }) => {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [inputMessage]);

  // Load conversation history on mount or when session changes
  useEffect(() => {
    try {
      setError(null);
      // If we have initial messages from a loaded conversation, use them
      if (initialMessages && initialMessages.length > 0) {
        // Convert StoredMessage to ChatMessage format
        const convertedMessages: ChatMessageType[] = initialMessages.map((msg) => ({
          role: msg.role,
          content: msg.content,
        }));
        setMessages(convertedMessages);
        console.log(`Loaded ${convertedMessages.length} messages for session ${sessionId}`);
      } else {
        // For new sessions, start with empty messages
        setMessages([]);
        console.log(`Starting new session ${sessionId} with empty messages`);
      }
    } catch (err) {
      console.error('Error loading messages:', err);
      setError(err instanceof Error ? err.message : 'Failed to load messages');
      setMessages([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessageType = {
      role: 'user',
      content: inputMessage,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Save user message to conversation
      try {
        await apiClient.addMessage(sessionId, 'user', inputMessage);
      } catch (err) {
        console.error('Failed to save user message:', err);
      }

      if (useStreaming) {
        // Streaming mode
        const assistantMessage: ChatMessageType = {
          role: 'assistant',
          content: '',
        };
        setMessages((prev) => [...prev, assistantMessage]);

        const stream = apiClient.chatStream({
          message: inputMessage,
          session_id: sessionId,
          task_type: taskType,
          stream: true,
        });

        for await (const chunk of stream) {
          assistantMessage.content += chunk;
          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = { ...assistantMessage };
            return newMessages;
          });
        }

        // Save assistant message to conversation
        try {
          await apiClient.addMessage(sessionId, 'assistant', assistantMessage.content);
        } catch (err) {
          console.error('Failed to save assistant message:', err);
        }
      } else {
        // Non-streaming mode
        const response = await apiClient.chat({
          message: inputMessage,
          session_id: sessionId,
          task_type: taskType,
        });

        const assistantMessage: ChatMessageType = {
          role: 'assistant',
          content: response.response,
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // Save assistant message to conversation
        try {
          await apiClient.addMessage(sessionId, 'assistant', response.response);
        } catch (err) {
          console.error('Failed to save assistant message:', err);
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      setError(`Failed to send message: ${errorMsg}`);
      const errorMessage: ChatMessageType = {
        role: 'assistant',
        content: `Error: ${errorMsg}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearHistory = async () => {
    try {
      await apiClient.clearHistory(sessionId);
      setMessages([]);
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#FAF9F7]">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-5 h-5 text-red-500 mt-0.5">
                  <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-sm text-red-800">{error}</p>
                  <button
                    onClick={() => setError(null)}
                    className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          )}

          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#DA7756] to-[#C86A4A] flex items-center justify-center mb-6">
                <span className="text-white font-bold text-2xl">C</span>
              </div>
              <h2 className="text-2xl font-semibold text-[#1A1A1A] mb-2">How can I help you code today?</h2>
              <p className="text-[#666666] max-w-md">
                I can help you write, debug, and explain code.
                Currently using {taskType === 'reasoning' ? 'DeepSeek-R1 for reasoning' : 'Qwen3 for coding'}.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))}
              {isLoading && messages[messages.length - 1]?.role === 'assistant' && messages[messages.length - 1]?.content === '' && (
                <div className="flex items-center gap-2 text-[#666666]">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-[#DA7756] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-[#DA7756] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-[#DA7756] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <span className="text-sm">Thinking...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-[#E5E5E5] bg-white">
        <div className="max-w-3xl mx-auto px-4 py-4">
          {/* Options Bar */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-[#666666] cursor-pointer">
                <input
                  type="checkbox"
                  checked={useStreaming}
                  onChange={(e) => setUseStreaming(e.target.checked)}
                  className="w-4 h-4 rounded border-[#E5E5E5] text-[#DA7756] focus:ring-[#DA7756] focus:ring-offset-0"
                />
                <span>Stream response</span>
              </label>
            </div>
            <button
              onClick={handleClearHistory}
              className="text-sm text-[#666666] hover:text-[#1A1A1A] flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
              </svg>
              Clear
            </button>
          </div>

          {/* Input Box */}
          <div className="relative">
            <textarea
              ref={textareaRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Message Code Agent..."
              className="w-full px-4 py-3 pr-14 bg-[#F5F4F2] text-[#1A1A1A] placeholder-[#999999] rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-[#DA7756] focus:ring-opacity-50 border border-[#E5E5E5]"
              rows={1}
              disabled={isLoading}
              style={{ minHeight: '48px', maxHeight: '200px' }}
            />
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !inputMessage.trim()}
              className="absolute right-2 bottom-2 p-2 rounded-xl bg-[#DA7756] hover:bg-[#C86A4A] disabled:bg-[#E5E5E5] disabled:cursor-not-allowed text-white transition-colors"
            >
              {isLoading ? (
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              )}
            </button>
          </div>
          <p className="mt-2 text-xs text-[#999999] text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
