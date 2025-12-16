/**
 * WorkflowInterface component - Claude.ai inspired multi-agent workflow UI
 */
import { useState, useRef, useEffect } from 'react';
import { WorkflowUpdate } from '../types/api';
import WorkflowStep from './WorkflowStep';
import apiClient from '../api/client';

interface WorkflowInterfaceProps {
  sessionId: string;
  initialUpdates?: WorkflowUpdate[];
}

const WorkflowInterface = ({ sessionId, initialUpdates }: WorkflowInterfaceProps) => {
  const [input, setInput] = useState('');
  const [updates, setUpdates] = useState<WorkflowUpdate[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [updates]);

  // Load initial updates when session changes
  useEffect(() => {
    if (initialUpdates && initialUpdates.length > 0) {
      setUpdates(initialUpdates);
      console.log(`Loaded ${initialUpdates.length} workflow updates for session ${sessionId}`);
    } else {
      setUpdates([]);
      console.log(`Starting new workflow session ${sessionId}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Save workflow state after updates complete
  const saveWorkflowState = async (workflowUpdates: WorkflowUpdate[]) => {
    try {
      await apiClient.updateConversation(sessionId, undefined, {
        updates: workflowUpdates,
      });
    } catch (err) {
      console.error('Failed to save workflow state:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isRunning) return;

    const userMessage = input.trim();
    setInput('');
    setUpdates([]);
    setIsRunning(true);

    // Create/update conversation for workflow
    try {
      await apiClient.createConversation(sessionId, userMessage.slice(0, 50), 'workflow');
    } catch (err) {
      // Conversation might already exist, continue
      console.log('Conversation may already exist:', err);
    }

    // Save user message
    try {
      await apiClient.addMessage(sessionId, 'user', userMessage);
    } catch (err) {
      console.error('Failed to save user message:', err);
    }

    const allUpdates: WorkflowUpdate[] = [];

    try {
      const response = await fetch('/api/workflow/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No reader available');
      }

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim());

        for (const line of lines) {
          try {
            const update: WorkflowUpdate = JSON.parse(line);

            // Track all updates for saving
            const existingIndex = allUpdates.findIndex(u => u.agent === update.agent);
            if (existingIndex >= 0) {
              allUpdates[existingIndex] = update;
            } else {
              allUpdates.push(update);
            }

            setUpdates(prev => {
              const existingIndex = prev.findIndex(u => u.agent === update.agent);
              if (existingIndex >= 0) {
                // Replace existing update for this agent
                const newUpdates = [...prev];
                newUpdates[existingIndex] = update;
                return newUpdates;
              } else {
                // Add new agent step
                return [...prev, update];
              }
            });

            // Save artifacts when they're created
            if (update.type === 'artifact' && update.artifact) {
              try {
                await apiClient.addArtifact(
                  sessionId,
                  update.artifact.filename,
                  update.artifact.language,
                  update.artifact.content
                );
              } catch (err) {
                console.error('Failed to save artifact:', err);
              }
            }
          } catch (e) {
            console.error('Error parsing update:', e);
          }
        }
      }

      // Save final workflow state
      await saveWorkflowState(allUpdates);
    } catch (error) {
      console.error('Error executing workflow:', error);
      setUpdates(prev => [
        ...prev,
        {
          agent: 'Workflow',
          type: 'error',
          status: 'error',
          message: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        },
      ]);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#FAF9F7]">
      {/* Workflow Steps Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {updates.length === 0 && !isRunning && (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#DA7756] to-[#C86A4A] flex items-center justify-center mb-6 shadow-lg">
                <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                </svg>
              </div>
              <h2 className="text-2xl font-semibold text-[#1A1A1A] mb-3">Multi-Agent Workflow</h2>
              <p className="text-[#666666] max-w-md mb-6">
                Enter a coding task and watch the agents collaborate to plan, code, and review your request.
              </p>
              <div className="flex items-center gap-4 text-sm text-[#999999]">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#DA7756]"></div>
                  <span>Planning</span>
                </div>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#16A34A]"></div>
                  <span>Coding</span>
                </div>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#2563EB]"></div>
                  <span>Review</span>
                </div>
              </div>
            </div>
          )}

          {updates.length > 0 && (
            <div className="space-y-4">
              {updates.map((update, index) => (
                <WorkflowStep key={`${update.agent}-${index}`} update={update} />
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-[#E5E5E5] bg-white">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <form onSubmit={handleSubmit}>
            <div className="relative">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Describe your coding task..."
                disabled={isRunning}
                className="w-full px-4 py-3 pr-32 bg-[#F5F4F2] text-[#1A1A1A] placeholder-[#999999] rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#DA7756] focus:ring-opacity-50 border border-[#E5E5E5] disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isRunning || !input.trim()}
                className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 rounded-xl bg-[#DA7756] hover:bg-[#C86A4A] disabled:bg-[#E5E5E5] disabled:cursor-not-allowed text-white font-medium text-sm transition-colors flex items-center gap-2"
              >
                {isRunning ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Running</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
                    </svg>
                    <span>Execute</span>
                  </>
                )}
              </button>
            </div>
          </form>
          <p className="mt-2 text-xs text-[#999999] text-center">
            The workflow will automatically plan, implement, and review your request
          </p>
        </div>
      </div>
    </div>
  );
};

export default WorkflowInterface;
