/**
 * Main App component - Unified AI Code Assistant
 */
import { useState, useEffect } from 'react';
import WorkflowInterface from './components/WorkflowInterface';
import Terminal from './components/Terminal';
import PromptLibrary from './components/PromptLibrary';
import { WorkflowUpdate } from './types/api';
import apiClient from './api/client';

interface FrameworkInfo {
  framework: string;
  agent_manager: string;
  workflow_manager: string;
}

function App() {
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const [frameworkInfo, setFrameworkInfo] = useState<FrameworkInfo | null>(null);
  const [workspace, setWorkspace] = useState<string>('/home/user/workspace');
  const [showTerminal, setShowTerminal] = useState(false);
  const [showPromptLibrary, setShowPromptLibrary] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<string>('');

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

  const handleWorkspaceChange = async (newWorkspace: string) => {
    setWorkspace(newWorkspace);
    // Notify backend of workspace change
    try {
      await apiClient.setWorkspace(sessionId, newWorkspace);
      // Reload the interface to show new workspace/project
      setLoadedWorkflowState([]);
    } catch (err) {
      console.error('Failed to set workspace:', err);
    }
  };

  const handlePromptSelect = (prompt: string) => {
    setSelectedPrompt(prompt);
    setShowPromptLibrary(false);
  };

  return (
    <div className="flex h-screen bg-[#FAF9F7]">
      {/* Main Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E5E5E5] flex items-center justify-between bg-white">
          {/* Left Section: Logo */}
          <div className="flex items-center gap-4">
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

          {/* Right Section: Actions & Session Info */}
          <div className="flex items-center gap-4">
            {/* Unified Workflow Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-r from-[#8B5CF6] to-[#DA7756] text-white">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
              </svg>
              <span className="text-xs font-medium">Unified LangGraph</span>
            </div>

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

            {/* Prompt Library Button */}
            <button
              onClick={() => setShowPromptLibrary(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#8B5CF6] text-white hover:bg-[#7C3AED] transition-colors"
              title="Open Prompt Library"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
              </svg>
              <span className="text-xs font-medium">Prompts</span>
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
            selectedPrompt={selectedPrompt}
            onPromptUsed={() => setSelectedPrompt('')}
            onWorkspaceChange={handleWorkspaceChange}
          />
        </div>
      </div>

      {/* Prompt Library */}
      <PromptLibrary
        isOpen={showPromptLibrary}
        onClose={() => setShowPromptLibrary(false)}
        onPromptSelect={handlePromptSelect}
      />

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
