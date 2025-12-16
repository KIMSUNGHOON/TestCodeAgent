/**
 * ConversationList component - Claude.ai inspired sidebar
 */
import { useState, useEffect } from 'react';
import { Conversation } from '../types/api';
import apiClient from '../api/client';

interface ConversationListProps {
  currentSessionId: string;
  mode: 'chat' | 'workflow';
  onSelectConversation: (conversation: Conversation) => void;
  onNewConversation: () => void;
}

const ConversationList = ({
  currentSessionId,
  mode,
  onSelectConversation,
  onNewConversation,
}: ConversationListProps) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadConversations();
  }, [mode]);

  const loadConversations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.listConversations(50, 0, mode);
      setConversations(response.conversations);
    } catch (err) {
      console.error('Failed to load conversations:', err);
      setError('Failed to load conversations');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;

    try {
      await apiClient.deleteConversation(sessionId);
      setConversations((prev) => prev.filter((c) => c.session_id !== sessionId));
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
      return 'Yesterday';
    } else if (days < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div className="w-72 bg-[#FAF9F7] border-r border-[#E5E5E5] flex flex-col h-full">
      {/* Header with New Button */}
      <div className="p-4">
        <button
          onClick={onNewConversation}
          className="w-full px-4 py-2.5 bg-white hover:bg-[#F5F4F2] text-[#1A1A1A] rounded-xl border border-[#E5E5E5] flex items-center justify-center gap-2 transition-colors shadow-sm"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span className="font-medium">New {mode === 'workflow' ? 'Workflow' : 'Chat'}</span>
        </button>
      </div>

      {/* Section Title */}
      <div className="px-4 py-2">
        <h3 className="text-xs font-medium text-[#999999] uppercase tracking-wider">
          Recent
        </h3>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin h-5 w-5 border-2 border-[#DA7756] border-t-transparent rounded-full"></div>
          </div>
        ) : error ? (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-red-500">{error}</p>
            <button
              onClick={loadConversations}
              className="mt-2 text-sm text-[#DA7756] hover:underline"
            >
              Try again
            </button>
          </div>
        ) : conversations.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[#F5F4F2] flex items-center justify-center">
              <svg className="w-6 h-6 text-[#999999]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
              </svg>
            </div>
            <p className="text-sm text-[#666666]">No conversations yet</p>
            <p className="text-xs text-[#999999] mt-1">Start a new one above</p>
          </div>
        ) : (
          <div className="space-y-1">
            {conversations.map((conversation) => (
              <div
                key={conversation.session_id}
                onClick={() => onSelectConversation(conversation)}
                className={`group p-3 rounded-xl cursor-pointer transition-all ${
                  conversation.session_id === currentSessionId
                    ? 'bg-white shadow-sm border border-[#E5E5E5]'
                    : 'hover:bg-white hover:shadow-sm'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-[#1A1A1A] truncate leading-tight">
                      {conversation.title || 'Untitled'}
                    </h3>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className="text-xs text-[#999999]">
                        {formatDate(conversation.updated_at)}
                      </span>
                      <span className="text-xs text-[#999999]">
                        {conversation.message_count} msg
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, conversation.session_id)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-[#999999] hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                    title="Delete conversation"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-[#E5E5E5]">
        <button
          onClick={loadConversations}
          className="w-full px-3 py-2 text-sm text-[#666666] hover:text-[#1A1A1A] hover:bg-white rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          Refresh
        </button>
      </div>
    </div>
  );
};

export default ConversationList;
