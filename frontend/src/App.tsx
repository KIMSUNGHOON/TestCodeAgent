/**
 * Main App component - Claude.ai inspired UI
 */
import { useState, useCallback, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import WorkflowInterface from './components/WorkflowInterface';
import AgentStatus from './components/AgentStatus';
import ConversationList from './components/ConversationList';
import { Conversation, StoredMessage, WorkflowUpdate } from './types/api';
import apiClient from './api/client';

type Mode = 'chat' | 'workflow';

interface FrameworkInfo {
  framework: string;
  agent_manager: string;
  workflow_manager: string;
}

function App() {
  const [sessionId, setSessionId] = useState(() => `session-${Date.now()}`);
  const [taskType, setTaskType] = useState<'reasoning' | 'coding'>('coding');
  const [mode, setMode] = useState<Mode>('workflow');
  const [showSidebar, setShowSidebar] = useState(true);
  const [frameworkInfo, setFrameworkInfo] = useState<FrameworkInfo | null>(null);

  // Loaded conversation state
  const [loadedMessages, setLoadedMessages] = useState<StoredMessage[]>([]);
  const [loadedWorkflowState, setLoadedWorkflowState] = useState<WorkflowUpdate[]>([]);

  // Load framework info on mount
  useEffect(() => {
    const loadFrameworkInfo = async () => {
      try {
        const info = await apiClient.getFrameworkInfo();
        setFrameworkInfo(info);
      } catch (err) {
        console.error('Failed to load framework info:', err);
      }
    };
    loadFrameworkInfo();
  }, []);

  const handleNewConversation = useCallback(() => {
    const newSessionId = `session-${Date.now()}`;
    setSessionId(newSessionId);
    setLoadedMessages([]);
    setLoadedWorkflowState([]);
  }, []);

  const handleSelectConversation = useCallback(async (conversation: Conversation) => {
    try {
      // Load full conversation with messages
      const fullConversation = await apiClient.getConversation(conversation.session_id);

      setSessionId(conversation.session_id);

      if (conversation.mode === 'workflow') {
        setMode('workflow');
        // Extract workflow updates from stored state (saved as { updates: [...] })
        if (fullConversation.workflow_state) {
          try {
            const workflowState = fullConversation.workflow_state as { updates?: WorkflowUpdate[] };
            if (workflowState && workflowState.updates && Array.isArray(workflowState.updates)) {
              setLoadedWorkflowState(workflowState.updates);
            } else {
              console.warn('Invalid workflow state format:', fullConversation.workflow_state);
              setLoadedWorkflowState([]);
            }
          } catch (parseErr) {
            console.error('Failed to parse workflow state:', parseErr);
            setLoadedWorkflowState([]);
          }
        } else {
          setLoadedWorkflowState([]);
        }
      } else {
        setMode('chat');
        setLoadedMessages(fullConversation.messages || []);
      }
    } catch (err) {
      console.error('Failed to load conversation:', err);
      alert(`Failed to load conversation: ${err instanceof Error ? err.message : 'Unknown error'}`);
      // Reset to new conversation on error
      handleNewConversation();
    }
  }, [handleNewConversation]);

  const handleModeChange = (newMode: Mode) => {
    setMode(newMode);
    // Create new session when switching modes
    handleNewConversation();
  };

  return (
    <div className="flex h-screen bg-[#FAF9F7]">
      {/* Conversation List Sidebar */}
      {showSidebar && (
        <ConversationList
          currentSessionId={sessionId}
          mode={mode}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
        />
      )}

      {/* Main Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E5E5E5] flex items-center justify-between bg-white">
          {/* Left Section: Toggle + Logo */}
          <div className="flex items-center gap-4">
            {/* Sidebar Toggle */}
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-2 text-[#666666] hover:text-[#1A1A1A] hover:bg-[#F5F4F2] rounded-lg"
              title={showSidebar ? 'Hide sidebar' : 'Show sidebar'}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>

            {/* Logo */}
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#DA7756] to-[#C86A4A] flex items-center justify-center">
                <span className="text-white font-semibold text-sm">C</span>
              </div>
              <span className="font-semibold text-[#1A1A1A]">Code Agent</span>
            </div>
          </div>

          {/* Mode Switcher */}
          <div className="flex bg-[#F5F4F2] rounded-lg p-1">
            <button
              onClick={() => handleModeChange('chat')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                mode === 'chat'
                  ? 'bg-white text-[#1A1A1A] shadow-sm'
                  : 'text-[#666666] hover:text-[#1A1A1A]'
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => handleModeChange('workflow')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                mode === 'workflow'
                  ? 'bg-white text-[#1A1A1A] shadow-sm'
                  : 'text-[#666666] hover:text-[#1A1A1A]'
              }`}
            >
              Workflow
            </button>
          </div>

          {/* Framework & Session Info */}
          <div className="flex items-center gap-4">
            {/* Framework Badge */}
            {frameworkInfo && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#F5F4F2] border border-[#E5E5E5]">
                <div className={`w-2 h-2 rounded-full ${
                  frameworkInfo.framework === 'langchain' ? 'bg-[#3B82F6]' :
                  frameworkInfo.framework === 'microsoft' ? 'bg-[#10B981]' :
                  'bg-[#8B5CF6]'
                }`}></div>
                <span className="text-xs font-medium text-[#666666]">
                  {frameworkInfo.framework === 'langchain' ? 'LangChain' :
                   frameworkInfo.framework === 'microsoft' ? 'Microsoft' :
                   frameworkInfo.framework.charAt(0).toUpperCase() + frameworkInfo.framework.slice(1)}
                </span>
                <span className="text-[10px] text-[#999999] border-l border-[#E5E5E5] pl-2">
                  {frameworkInfo.workflow_manager.replace('WorkflowManager', '').replace('Workflow', '')}
                </span>
              </div>
            )}

            {/* Session Info */}
            <div className="flex items-center gap-2 text-sm text-[#999999]">
              <div className="w-2 h-2 rounded-full bg-[#16A34A]"></div>
              <span>{sessionId.slice(-8)}</span>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 overflow-hidden">
            {mode === 'chat' ? (
              <ChatInterface
                key={sessionId}
                sessionId={sessionId}
                taskType={taskType}
                initialMessages={loadedMessages}
              />
            ) : (
              <WorkflowInterface
                key={sessionId}
                sessionId={sessionId}
                initialUpdates={loadedWorkflowState}
              />
            )}
          </div>

          {/* Right Sidebar - only show in chat mode */}
          {mode === 'chat' && (
            <AgentStatus
              sessionId={sessionId}
              taskType={taskType}
              onTaskTypeChange={setTaskType}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
