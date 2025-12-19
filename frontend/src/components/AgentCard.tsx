/**
 * AgentCard - Enhanced agent status display
 * Shows agent progress, streaming content, and execution time
 */
import React, { useState } from 'react';
import StreamingCodeBlock from './StreamingCodeBlock';

interface Artifact {
  filename: string;
  language: string;
  content: string;
}

interface AgentCardProps {
  name: string;
  title: string;
  description: string;
  status: 'pending' | 'starting' | 'running' | 'streaming' | 'thinking' | 'completed' | 'error' | 'awaiting_approval';
  message?: string;
  executionTime?: number;
  artifacts?: Artifact[];
  streamingContent?: string;
  streamingFile?: string;
  thinkingContent?: string;
  isExpanded?: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600 border-gray-200',
  starting: 'bg-blue-50 text-blue-700 border-blue-200',
  running: 'bg-blue-50 text-blue-700 border-blue-300',
  streaming: 'bg-green-50 text-green-700 border-green-300',
  thinking: 'bg-purple-50 text-purple-700 border-purple-300',
  completed: 'bg-green-50 text-green-700 border-green-200',
  error: 'bg-red-50 text-red-700 border-red-200',
  awaiting_approval: 'bg-yellow-50 text-yellow-700 border-yellow-300',
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: (
    <div className="w-2 h-2 rounded-full bg-gray-400" />
  ),
  starting: (
    <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
  ),
  running: (
    <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
  ),
  streaming: (
    <div className="relative">
      <span className="flex h-3 w-3">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
      </span>
    </div>
  ),
  thinking: (
    <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
  ),
  completed: (
    <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  ),
  error: (
    <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
    </svg>
  ),
  awaiting_approval: (
    <svg className="w-5 h-5 text-yellow-500 animate-pulse" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
    </svg>
  ),
};

const formatTime = (seconds: number): string => {
  if (seconds < 1) return '<1s';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
};

export const AgentCard: React.FC<AgentCardProps> = ({
  name,
  title,
  description,
  status,
  message,
  executionTime,
  artifacts = [],
  streamingContent,
  streamingFile,
  thinkingContent,
  isExpanded: initialExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(initialExpanded || status === 'running' || status === 'streaming');

  const hasContent = artifacts.length > 0 || streamingContent || thinkingContent;
  const isActive = ['running', 'streaming', 'thinking', 'starting'].includes(status);

  return (
    <div className={`rounded-xl border-2 transition-all duration-300 ${STATUS_COLORS[status]} ${isActive ? 'shadow-md' : ''}`}>
      {/* Header */}
      <div
        className={`px-4 py-3 flex items-center justify-between cursor-pointer ${hasContent ? 'hover:bg-opacity-80' : ''}`}
        onClick={() => hasContent && setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          {/* Status Icon */}
          <div className="w-6 h-6 flex items-center justify-center">
            {STATUS_ICONS[status]}
          </div>

          {/* Agent Info */}
          <div>
            <h3 className="font-semibold text-sm">{title}</h3>
            <p className="text-xs opacity-75">{message || description}</p>
          </div>
        </div>

        {/* Right side info */}
        <div className="flex items-center gap-3">
          {/* Execution Time */}
          {executionTime !== undefined && (
            <span className="text-xs font-mono bg-white/50 px-2 py-1 rounded">
              ⏱️ {formatTime(executionTime)}
            </span>
          )}

          {/* Artifacts count */}
          {artifacts.length > 0 && (
            <span className="text-xs font-medium bg-white/50 px-2 py-1 rounded">
              📄 {artifacts.length} file{artifacts.length > 1 ? 's' : ''}
            </span>
          )}

          {/* Expand button */}
          {hasContent && (
            <svg
              className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && hasContent && (
        <div className="px-4 pb-4 space-y-3">
          {/* Thinking Content (DeepSeek-R1) */}
          {thinkingContent && (
            <div className="bg-purple-100/50 rounded-lg p-3 border border-purple-200">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
                <span className="text-xs font-medium text-purple-700">Thinking...</span>
              </div>
              <pre className="text-xs text-purple-800 whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
                {thinkingContent}
              </pre>
            </div>
          )}

          {/* Streaming Code */}
          {streamingContent && streamingFile && (
            <StreamingCodeBlock
              filename={streamingFile}
              language={streamingFile.split('.').pop() || 'text'}
              content={streamingContent}
              isStreaming={status === 'streaming'}
              agentTitle={title}
            />
          )}

          {/* Generated Artifacts */}
          {artifacts.map((artifact, index) => (
            <StreamingCodeBlock
              key={`${artifact.filename}-${index}`}
              filename={artifact.filename}
              language={artifact.language}
              content={artifact.content}
              isStreaming={false}
              agentTitle={title}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default AgentCard;
