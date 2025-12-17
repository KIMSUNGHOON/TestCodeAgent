/**
 * Main App component - Unified AI Code Assistant
 */
import { useState, useCallback, useEffect } from 'react';
import WorkflowInterface from './components/WorkflowInterface';
import ConversationList from './components/ConversationList';
import WorkspaceSettings from './components/WorkspaceSettings';
import Terminal from './components/Terminal';
import { Conversation, WorkflowUpdate } from './types/api';
import apiClient from './api/client';

interface FrameworkInfo {
  framework: string;
  agent_manager: string;
  workflow_manager: string;
}

function App() {
  const [sessionId, setSessionId] = useState(() => `session-${Date.now()}`);
  const [showSidebar, setShowSidebar] = useState(true);
  const [frameworkInfo, setFrameworkInfo] = useState<FrameworkInfo | null>(null);
  const [workspace, setWorkspace] = useState<string>('/home/user/workspace');
  const [showWorkspaceSettings, setShowWorkspaceSettings] = useState(false);
  const [showTerminal, setShowTerminal] = useState(false);

  // Loaded conversation state
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
    setLoadedWorkflowState([]);
  }, []);

  const handleSelectConversation = useCallback(async (conversation: Conversation) => {
    try {
      // Load full conversation with messages
      const fullConversation = await apiClient.getConversation(conversation.session_id);

      setSessionId(conversation.session_id);

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
    } catch (err) {
      console.error('Failed to load conversation:', err);
      alert(`Failed to load conversation: ${err instanceof Error ? err.message : 'Unknown error'}`);
      // Reset to new conversation on error
      handleNewConversation();
    }
  }, [handleNewConversation]);

  const handleWorkspaceChange = async (newWorkspace: string) => {
    setWorkspace(newWorkspace);
    // Notify backend of workspace change
    try {
      await apiClient.setWorkspace(sessionId, newWorkspace);
    } catch (err) {
      console.error('Failed to set workspace:', err);
    }
  };

  return (
    <div className="flex h-screen bg-[#FAF9F7]">
      {/* Conversation List Sidebar */}
      {showSidebar && (
        <ConversationList
          currentSessionId={sessionId}
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
              <div>
                <div className="font-semibold text-[#1A1A1A]">AI Code Assistant</div>
                <div className="text-[10px] text-[#999999]">Unified Chat & Workflow</div>
              </div>
            </div>
          </div>

          {/* Framework, Workspace & Session Info */}
          <div className="flex items-center gap-4">
            {/* Workspace Button */}
            <button
              onClick={() => setShowWorkspaceSettings(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#F5F4F2] border border-[#E5E5E5] hover:bg-[#E5E5E5] transition-colors"
              title={`Workspace: ${workspace}`}
            >
              <svg className="w-4 h-4 text-[#DA7756]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
              </svg>
              <span className="text-xs font-medium text-[#666666] max-w-[120px] truncate">
                {workspace.split('/').pop() || workspace}
              </span>
            </button>

            {/* Terminal Button */}
            <button
              onClick={() => setShowTerminal(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#1E1E1E] text-white hover:bg-[#2D2D2D] transition-colors"
              title="Open Terminal"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
              </svg>
              <span className="text-xs font-medium">Terminal</span>
            </button>

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
        <div className="flex-1 overflow-hidden">
          <WorkflowInterface
            key={sessionId}
            sessionId={sessionId}
            initialUpdates={loadedWorkflowState}
            workspace={workspace}
          />
        </div>
      </div>

      {/* Workspace Settings Modal */}
      {showWorkspaceSettings && (
        <WorkspaceSettings
          workspace={workspace}
          onWorkspaceChange={handleWorkspaceChange}
          onClose={() => setShowWorkspaceSettings(false)}
        />
      )}

      {/* Terminal Modal */}
      <Terminal
        sessionId={sessionId}
        workspace={workspace}
        isVisible={showTerminal}
        onClose={() => setShowTerminal(false)}
      />
    </div>
  );
}

export default App;
