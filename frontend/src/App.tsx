/**
 * Main App component - Claude Web Style AI Code Assistant
 * 전체 브라우저 크기에 맞춰 반응형 레이아웃
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
    try {
      await apiClient.setWorkspace(sessionId, newWorkspace);
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
    <div className="flex flex-col w-screen h-screen bg-gray-950 text-gray-100 overflow-hidden">
      {/* Minimal Header - Claude Web Style */}
      <header className="flex-shrink-0 h-12 px-3 sm:px-4 flex items-center justify-between border-b border-gray-800 bg-gray-900">
        {/* Logo */}
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center">
            <span className="text-white font-semibold text-xs sm:text-sm">C</span>
          </div>
          <div className="hidden sm:block">
            <div className="font-medium text-sm text-gray-100">AI Code Agent</div>
            <div className="text-[10px] text-gray-500">LangGraph Workflow</div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Framework Badge - Hidden on mobile */}
          {frameworkInfo && (
            <div className="hidden md:flex items-center gap-2 px-2 py-1 rounded bg-gray-800 text-xs">
              <div className={`w-1.5 h-1.5 rounded-full ${
                frameworkInfo.framework === 'langchain' ? 'bg-blue-500' :
                frameworkInfo.framework === 'microsoft' ? 'bg-green-500' :
                'bg-purple-500'
              }`}></div>
              <span className="text-gray-400">
                {frameworkInfo.framework === 'langchain' ? 'LangChain' :
                 frameworkInfo.framework === 'microsoft' ? 'Microsoft' :
                 frameworkInfo.framework}
              </span>
            </div>
          )}

          {/* Prompt Library */}
          <button
            onClick={() => setShowPromptLibrary(true)}
            className="p-1.5 sm:p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-gray-200 transition-colors"
            title="프롬프트 라이브러리"
          >
            <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
            </svg>
          </button>

          {/* Terminal */}
          <button
            onClick={() => setShowTerminal(true)}
            className="p-1.5 sm:p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-gray-200 transition-colors"
            title="터미널"
          >
            <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
            </svg>
          </button>

          {/* Session Status */}
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>
            <span className="hidden sm:inline">{sessionId.slice(-8)}</span>
          </div>
        </div>
      </header>

      {/* Main Content - Full remaining height */}
      <main className="flex-1 min-h-0 overflow-hidden">
        <WorkflowInterface
          key={sessionId}
          sessionId={sessionId}
          initialUpdates={loadedWorkflowState}
          workspace={workspace}
          selectedPrompt={selectedPrompt}
          onPromptUsed={() => setSelectedPrompt('')}
          onWorkspaceChange={handleWorkspaceChange}
        />
      </main>

      {/* Modals */}
      <PromptLibrary
        isOpen={showPromptLibrary}
        onClose={() => setShowPromptLibrary(false)}
        onPromptSelect={handlePromptSelect}
      />

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
