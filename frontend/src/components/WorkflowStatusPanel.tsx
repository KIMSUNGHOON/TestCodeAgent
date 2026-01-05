/**
 * WorkflowStatusPanel - Compact right sidebar
 * Claude Code inspired: terminal-like, minimal, efficient
 */
import { useState } from 'react';
import { Artifact } from '../types/api';

interface AgentProgressStatus {
  name: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  executionTime?: number;
  streamingContent?: string;
  tokenUsage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

interface FileTreeNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  language?: string;
  saved?: boolean;
  savedPath?: string;
  relativePath?: string;
  description?: string;
  content?: string;
  action?: 'created' | 'modified';
  sizeBytes?: number;
  children?: FileTreeNode[];
}

interface WorkflowStatusPanelProps {
  isRunning: boolean;
  agents: AgentProgressStatus[];
  currentAgent?: string;
  totalProgress: number;
  elapsedTime: number;
  estimatedTimeRemaining?: number;
  streamingContent?: string;
  streamingFile?: string;
  savedFiles?: Artifact[];
  workspaceRoot?: string;
  projectName?: string;
  projectDir?: string;
}

const WorkflowStatusPanel = ({
  isRunning,
  agents,
  streamingContent,
  savedFiles,
  projectDir,
}: WorkflowStatusPanelProps) => {
  const [expandedSections, setExpandedSections] = useState({
    output: true,
    files: true,
  });

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Build file tree
  const buildFileTree = (files: Artifact[]): FileTreeNode[] => {
    const root: Map<string, FileTreeNode> = new Map();

    files.forEach(file => {
      const parts = file.filename.split('/');
      let currentLevel = root;

      parts.forEach((part, index) => {
        const isLastPart = index === parts.length - 1;
        const currentPath = parts.slice(0, index + 1).join('/');

        if (!currentLevel.has(part)) {
          const node: FileTreeNode = {
            name: part,
            path: currentPath,
            type: isLastPart ? 'file' : 'directory',
            ...(isLastPart && {
              language: file.language,
              saved: file.saved,
              savedPath: file.saved_path || undefined,
              relativePath: file.relative_path,
              description: file.description,
              content: file.content?.slice(0, 100),
              action: file.action,
              sizeBytes: file.size_bytes,
            }),
          };
          if (!isLastPart) node.children = [];
          currentLevel.set(part, node);
        }

        if (!isLastPart) {
          const existingNode = currentLevel.get(part)!;
          if (!existingNode.children) existingNode.children = [];
          const childMap = new Map<string, FileTreeNode>();
          existingNode.children.forEach(child => childMap.set(child.name, child));
          currentLevel = childMap;
          existingNode.children = Array.from(childMap.values());
        }
      });
    });

    return Array.from(root.values());
  };

  // File icon by extension
  const getFileIcon = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    const icons: Record<string, string> = {
      py: '🐍', js: '📜', ts: '📜', tsx: '⚛️', jsx: '⚛️',
      html: '🌐', css: '🎨', json: '⚙️', md: '📝',
      yml: '🔧', yaml: '🔧', sql: '🗄️', sh: '💻',
    };
    return icons[ext] || '📄';
  };

  const renderFileTree = (nodes: FileTreeNode[], depth: number = 0): JSX.Element[] => {
    return nodes
      .sort((a, b) => {
        if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
        return a.name.localeCompare(b.name);
      })
      .map(node => (
        <div key={node.path} style={{ paddingLeft: depth * 12 }}>
          <div className="flex items-center gap-1.5 py-0.5 px-1 rounded hover:bg-gray-700/50 text-xs group">
            {node.type === 'directory' ? (
              <>
                <span className="text-yellow-500">📁</span>
                <span className="text-yellow-400">{node.name}/</span>
              </>
            ) : (
              <>
                <span>{getFileIcon(node.name)}</span>
                <span className="text-gray-300 truncate flex-1">{node.name}</span>
                {node.action && (
                  <span className={`text-[9px] px-1 rounded ${
                    node.action === 'created' ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'
                  }`}>
                    {node.action === 'created' ? '+' : '~'}
                  </span>
                )}
                {node.sizeBytes !== undefined && (
                  <span className="text-[9px] text-gray-600">
                    {node.sizeBytes < 1024 ? `${node.sizeBytes}B` : `${(node.sizeBytes / 1024).toFixed(1)}K`}
                  </span>
                )}
              </>
            )}
          </div>
          {node.children && node.children.length > 0 && renderFileTree(node.children, depth + 1)}
        </div>
      ));
  };

  const fileTree = savedFiles && savedFiles.length > 0 ? buildFileTree(savedFiles) : [];
  const createdCount = savedFiles?.filter(f => f.action === 'created').length || 0;
  const modifiedCount = savedFiles?.filter(f => f.action === 'modified').length || 0;

  return (
    <div className="h-full flex flex-col bg-gray-900 text-gray-100 text-sm">
      {/* Header */}
      <div className="px-3 py-2 bg-gray-800 border-b border-gray-700 flex items-center justify-between">
        <span className="font-medium text-xs text-gray-400">OUTPUT</span>
        {isRunning ? (
          <span className="flex items-center gap-1 text-[10px] text-green-400">
            <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
            Live
          </span>
        ) : savedFiles && savedFiles.length > 0 ? (
          <span className="text-[10px] text-gray-500">✓ Done</span>
        ) : null}
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {/* Live Output */}
        {(isRunning || streamingContent) && (
          <div className="border-b border-gray-800">
            <button
              onClick={() => toggleSection('output')}
              className="w-full px-3 py-1.5 flex items-center justify-between text-xs font-medium text-gray-400 hover:bg-gray-800/50"
            >
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                Terminal
              </span>
              <span className="text-gray-600">{expandedSections.output ? '▼' : '▶'}</span>
            </button>
            {expandedSections.output && streamingContent && (
              <div className="px-3 pb-2">
                <pre className="font-mono text-[11px] text-gray-300 bg-black/30 p-2 rounded max-h-40 overflow-auto whitespace-pre-wrap leading-relaxed">
                  {streamingContent}
                  {isRunning && <span className="inline-block w-1.5 h-3 bg-green-400 animate-pulse ml-0.5" />}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Files */}
        {savedFiles && savedFiles.length > 0 && (
          <div>
            <button
              onClick={() => toggleSection('files')}
              className="w-full px-3 py-1.5 flex items-center justify-between text-xs font-medium text-gray-400 hover:bg-gray-800/50"
            >
              <span className="flex items-center gap-2">
                <span>Files</span>
                <span className="px-1.5 py-0.5 bg-gray-700 rounded text-[10px]">{savedFiles.length}</span>
                {createdCount > 0 && (
                  <span className="px-1 py-0.5 bg-green-500/20 text-green-400 rounded text-[10px]">+{createdCount}</span>
                )}
                {modifiedCount > 0 && (
                  <span className="px-1 py-0.5 bg-amber-500/20 text-amber-400 rounded text-[10px]">~{modifiedCount}</span>
                )}
              </span>
              <span className="text-gray-600">{expandedSections.files ? '▼' : '▶'}</span>
            </button>
            {expandedSections.files && (
              <div className="px-2 pb-2">
                {/* Project Path */}
                {projectDir && (
                  <div className="px-2 py-1 mb-1 text-[10px] text-gray-500 font-mono truncate border-b border-gray-800">
                    {projectDir}
                  </div>
                )}
                {/* File Tree */}
                <div className="bg-gray-800/30 rounded p-1">
                  {renderFileTree(fileTree)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Agent Details - Compact list */}
        {agents.some(a => a.status !== 'pending') && (
          <div className="px-3 py-2 border-t border-gray-800">
            <div className="text-[10px] text-gray-500 mb-1.5">AGENTS</div>
            <div className="space-y-1">
              {agents.filter(a => a.status !== 'pending').map(agent => (
                <div key={agent.name} className="flex items-center gap-2 text-[11px]">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    agent.status === 'running' ? 'bg-blue-500 animate-pulse' :
                    agent.status === 'completed' ? 'bg-green-500' :
                    agent.status === 'error' ? 'bg-red-500' : 'bg-gray-600'
                  }`} />
                  <span className={`flex-1 truncate ${
                    agent.status === 'running' ? 'text-blue-400' :
                    agent.status === 'completed' ? 'text-gray-400' :
                    agent.status === 'error' ? 'text-red-400' : 'text-gray-500'
                  }`}>
                    {agent.title.replace(/^[\p{Emoji}]\s*/u, '')}
                  </span>
                  {agent.executionTime !== undefined && (
                    <span className="text-gray-600 font-mono text-[10px]">{agent.executionTime.toFixed(1)}s</span>
                  )}
                  {agent.tokenUsage?.totalTokens ? (
                    <span className="text-gray-600 font-mono text-[10px]">{agent.tokenUsage.totalTokens.toLocaleString()}</span>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Stats */}
      {savedFiles && savedFiles.length > 0 && (
        <div className="px-3 py-1.5 bg-gray-800 border-t border-gray-700 flex items-center justify-between text-[10px] text-gray-500">
          <span>{savedFiles.filter(f => f.saved).length}/{savedFiles.length} saved</span>
          {!isRunning && <span className="text-green-500">Complete</span>}
        </div>
      )}
    </div>
  );
};

export default WorkflowStatusPanel;
