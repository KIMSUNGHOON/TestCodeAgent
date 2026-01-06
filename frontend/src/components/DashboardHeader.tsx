/**
 * DashboardHeader - Compact, responsive header
 * Claude Code inspired: minimal, dark, efficient
 */
import { useEffect, useState } from 'react';

interface AgentStatus {
  name: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  executionTime?: number;
  tokenUsage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

interface DashboardHeaderProps {
  projectName?: string;
  projectDir?: string;
  workspace?: string;
  isRunning: boolean;
  totalProgress: number;
  elapsedTime: number;
  estimatedTimeRemaining?: number;
  agents: AgentStatus[];
  onWorkspaceClick?: () => void;
}

const DashboardHeader = ({
  projectName,
  projectDir,
  workspace,
  isRunning,
  totalProgress,
  elapsedTime,
  estimatedTimeRemaining,
  agents,
  onWorkspaceClick,
}: DashboardHeaderProps) => {
  /**
   * Format time as hh:mm:ss or mm:ss or ss.sss
   * - Under 1 second: "0.123s" (3 decimal places)
   * - Under 60 seconds: "45s" or "45.5s"
   * - Under 1 hour: "12:34" (mm:ss)
   * - 1 hour+: "01:23:45" (hh:mm:ss)
   */
  const formatTime = (seconds: number): string => {
    if (seconds < 1) {
      return `${seconds.toFixed(3)}s`;
    }
    if (seconds < 60) {
      // Show 1 decimal for times under 60s if there's a fractional part
      return seconds % 1 === 0 ? `${seconds.toFixed(0)}s` : `${seconds.toFixed(1)}s`;
    }

    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const completedCount = agents.filter(a => a.status === 'completed').length;

  // Calculate total token usage
  const totalTokens = agents.reduce((sum, agent) => {
    return sum + (agent.tokenUsage?.totalTokens || 0);
  }, 0);

  // Animated progress
  const [animatedProgress, setAnimatedProgress] = useState(0);
  useEffect(() => {
    const timer = setTimeout(() => setAnimatedProgress(totalProgress), 50);
    return () => clearTimeout(timer);
  }, [totalProgress]);

  return (
    <div className="bg-gray-900 text-gray-100 border-b border-gray-700">
      {/* Main Header Row - Compact */}
      <div className="px-3 py-2 flex items-center justify-between gap-3">
        {/* Left: Status + Project */}
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Status Dot */}
          <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
            isRunning ? 'bg-blue-500 animate-pulse' :
            totalProgress >= 100 ? 'bg-green-500' : 'bg-gray-500'
          }`} />

          {/* Project Name */}
          <span className="font-medium text-sm truncate">
            {projectName || 'Project'}
          </span>

          {/* Status Badge */}
          {isRunning && (
            <span className="px-1.5 py-0.5 text-[10px] font-medium bg-blue-500/20 text-blue-400 rounded">
              Running
            </span>
          )}
        </div>

        {/* Center: Progress Info */}
        <div className="flex items-center gap-3 text-xs text-gray-400">
          {/* Agent Progress */}
          <span className="hidden sm:inline">
            {completedCount}/{agents.length} agents
          </span>

          {/* Token Count */}
          {totalTokens > 0 && (
            <span className="font-mono hidden md:inline">
              {totalTokens.toLocaleString()} tokens
            </span>
          )}
        </div>

        {/* Right: Time + Progress */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Elapsed Time */}
          <span className="font-mono text-sm font-medium">
            {formatTime(elapsedTime)}
          </span>

          {/* Progress Percentage */}
          <span className={`text-sm font-medium ${
            isRunning ? 'text-blue-400' : 'text-green-400'
          }`}>
            {Math.round(animatedProgress)}%
          </span>
        </div>
      </div>

      {/* Progress Bar - Thin */}
      <div className="h-0.5 bg-gray-800">
        <div
          className={`h-full transition-all duration-300 ${
            isRunning ? 'bg-blue-500' : 'bg-green-500'
          }`}
          style={{ width: `${animatedProgress}%` }}
        />
      </div>

      {/* Agent Pipeline - Compact, Horizontal Scroll */}
      {(isRunning || totalProgress > 0) && (
        <div className="px-3 py-1.5 bg-gray-800/50 overflow-x-auto scrollbar-thin">
          <div className="flex items-center gap-0.5 min-w-max">
            {agents.map((agent, index) => {
              const emoji = agent.title.match(/^[\p{Emoji}]/u)?.[0] || '';
              const shortName = agent.title.replace(/^[\p{Emoji}]\s*/u, '').split(' ')[0];

              return (
                <div key={agent.name} className="flex items-center">
                  {/* Agent Pill */}
                  <div
                    className={`
                      flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium
                      transition-all cursor-default
                      ${agent.status === 'running'
                        ? 'bg-blue-500/20 text-blue-400 ring-1 ring-blue-500/50'
                        : agent.status === 'completed'
                          ? 'bg-green-500/10 text-green-400'
                          : agent.status === 'error'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-gray-700/50 text-gray-500'}
                    `}
                    title={`${agent.title}: ${agent.description}${agent.executionTime ? ` (${agent.executionTime.toFixed(1)}s)` : ''}`}
                  >
                    {agent.status === 'running' ? (
                      <div className="w-2 h-2 border border-blue-400 border-t-transparent rounded-full animate-spin" />
                    ) : agent.status === 'completed' ? (
                      <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                    ) : agent.status === 'error' ? (
                      <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    ) : null}
                    <span>{emoji}{shortName}</span>
                  </div>

                  {/* Connector */}
                  {index < agents.length - 1 && (
                    <span className={`mx-0.5 ${
                      agent.status === 'completed' ? 'text-green-600' : 'text-gray-600'
                    }`}>→</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Path Row - Clickable, very compact */}
      <button
        onClick={onWorkspaceClick}
        className="w-full px-3 py-1 flex items-center gap-1.5 text-[11px] text-gray-500 hover:text-gray-400 hover:bg-gray-800/50 transition-colors text-left"
      >
        <svg className="w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
        </svg>
        <span className="font-mono truncate">{projectDir || workspace || '~/workspace'}</span>
        {estimatedTimeRemaining !== undefined && estimatedTimeRemaining > 0 && (
          <span className="ml-auto text-gray-600">ETA ~{formatTime(estimatedTimeRemaining)}</span>
        )}
      </button>
    </div>
  );
};

export default DashboardHeader;
