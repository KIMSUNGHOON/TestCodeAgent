/**
 * WorkflowProgress - Enhanced progress indicator with ETA and agent times
 */
import React from 'react';

interface AgentStatus {
  name: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  executionTime?: number;
  icon?: string;
}

interface WorkflowProgressProps {
  agents: AgentStatus[];
  currentAgent?: string;
  totalProgress: number;
  estimatedTimeRemaining?: number;
  elapsedTime: number;
  isRunning: boolean;
}

const AGENT_ICONS: Record<string, string> = {
  supervisor: '🧠',
  architect: '🏗️',
  coder: '💻',
  reviewer: '👀',
  qa_gate: '🧪',
  security_gate: '🔒',
  refiner: '🔧',
  aggregator: '📊',
  hitl: '👤',
  persistence: '💾',
  workflow: '✅',
  error: '❌',
};

const formatTime = (seconds: number): string => {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
};

export const WorkflowProgress: React.FC<WorkflowProgressProps> = ({
  agents,
  currentAgent,
  totalProgress,
  estimatedTimeRemaining,
  elapsedTime,
  isRunning,
}) => {
  const completedCount = agents.filter(a => a.status === 'completed').length;
  const totalCount = agents.length;

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {isRunning ? (
              <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center animate-pulse">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </div>
            )}
            <div>
              <h3 className="font-semibold text-gray-900">
                {isRunning ? '🔄 AI Development Pipeline' : '✅ Pipeline Complete'}
              </h3>
              <p className="text-sm text-gray-600">
                {completedCount}/{totalCount} agents completed
              </p>
            </div>
          </div>

          {/* Time Stats */}
          <div className="flex items-center gap-4 text-sm">
            <div className="text-gray-600">
              <span className="font-medium">Elapsed:</span> {formatTime(elapsedTime)}
            </div>
            {isRunning && estimatedTimeRemaining !== undefined && (
              <div className="text-blue-600">
                <span className="font-medium">ETA:</span> ~{formatTime(estimatedTimeRemaining)}
              </div>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-3">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ease-out ${
                  isRunning ? 'bg-blue-500' : 'bg-green-500'
                }`}
                style={{ width: `${totalProgress}%` }}
              />
            </div>
            <span className="text-sm font-mono text-gray-600 min-w-[3rem] text-right">
              {Math.round(totalProgress)}%
            </span>
          </div>
        </div>
      </div>

      {/* Agent Pipeline */}
      <div className="px-4 py-3">
        <div className="flex items-center gap-1 overflow-x-auto pb-2">
          {agents.map((agent, index) => (
            <React.Fragment key={agent.name}>
              <div
                className={`flex flex-col items-center min-w-[80px] p-2 rounded-lg transition-all ${
                  agent.status === 'running'
                    ? 'bg-blue-50 border-2 border-blue-300 scale-105'
                    : agent.status === 'completed'
                    ? 'bg-green-50 border border-green-200'
                    : agent.status === 'error'
                    ? 'bg-red-50 border border-red-200'
                    : 'bg-gray-50 border border-gray-200'
                }`}
              >
                {/* Agent Icon */}
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center text-xl ${
                    agent.status === 'running'
                      ? 'bg-blue-100 animate-pulse'
                      : agent.status === 'completed'
                      ? 'bg-green-100'
                      : agent.status === 'error'
                      ? 'bg-red-100'
                      : 'bg-gray-100'
                  }`}
                >
                  {AGENT_ICONS[agent.name] || '🤖'}
                </div>

                {/* Agent Name */}
                <span className="text-xs font-medium text-gray-700 mt-1 text-center truncate max-w-full">
                  {agent.title.replace(/^[^\s]+\s/, '')}
                </span>

                {/* Execution Time */}
                {agent.executionTime !== undefined && (
                  <span className="text-[10px] text-gray-500 mt-0.5">
                    {formatTime(agent.executionTime)}
                  </span>
                )}

                {/* Status Indicator */}
                <div className="mt-1">
                  {agent.status === 'running' && (
                    <span className="inline-flex h-2 w-2 rounded-full bg-blue-500 animate-ping" />
                  )}
                  {agent.status === 'completed' && (
                    <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  )}
                  {agent.status === 'error' && (
                    <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                  {agent.status === 'pending' && (
                    <span className="inline-block h-2 w-2 rounded-full bg-gray-300" />
                  )}
                </div>
              </div>

              {/* Arrow between agents */}
              {index < agents.length - 1 && (
                <svg
                  className={`w-4 h-4 flex-shrink-0 ${
                    agents[index + 1].status !== 'pending' ? 'text-green-400' : 'text-gray-300'
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Current Agent Detail */}
      {currentAgent && isRunning && (
        <div className="px-4 py-2 bg-blue-50 border-t border-blue-100">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-blue-700">
              <span className="font-medium">
                {agents.find(a => a.name === currentAgent)?.title || currentAgent}
              </span>
              {' - '}
              {agents.find(a => a.name === currentAgent)?.description || 'Processing...'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkflowProgress;
