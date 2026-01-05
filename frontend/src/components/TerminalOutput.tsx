/**
 * TerminalOutput - Claude Code inspired terminal-style output
 * Displays workflow updates as CLI-like streaming output
 */
import { useState } from 'react';
import { WorkflowUpdate, Artifact } from '../types/api';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface TerminalOutputProps {
  updates: WorkflowUpdate[];
  isRunning: boolean;
  liveOutputs: Map<string, {
    agentName: string;
    agentTitle: string;
    content: string;
    status: string;
    timestamp: number;
  }>;
}

interface ArtifactViewerProps {
  artifact: Artifact;
}

const ArtifactViewer = ({ artifact }: ArtifactViewerProps) => {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-1 border border-gray-700 rounded overflow-hidden">
      <div
        className="flex items-center justify-between px-2 py-1 bg-gray-800 cursor-pointer hover:bg-gray-700"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2 text-xs">
          <span className={`${artifact.saved ? 'text-green-400' : 'text-gray-400'}`}>
            {artifact.saved ? '✓' : '○'}
          </span>
          <span className="font-mono text-gray-300">{artifact.filename}</span>
          <span className="text-gray-600">[{artifact.language}]</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); handleCopy(); }}
            className="text-xs text-gray-500 hover:text-gray-300 px-1"
          >
            {copied ? 'copied!' : 'copy'}
          </button>
          <span className="text-gray-600 text-xs">{expanded ? '▼' : '▶'}</span>
        </div>
      </div>
      {expanded && (
        <SyntaxHighlighter
          style={oneDark}
          language={artifact.language}
          customStyle={{ margin: 0, borderRadius: 0, maxHeight: '300px', fontSize: '11px' }}
          showLineNumbers
        >
          {artifact.content}
        </SyntaxHighlighter>
      )}
    </div>
  );
};

const TerminalOutput = ({ updates, isRunning, liveOutputs }: TerminalOutputProps) => {
  // Get status icon as text
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
      case 'starting':
      case 'streaming':
        return '⋯';
      case 'thinking':
        return '◐';
      case 'completed':
        return '✓';
      case 'error':
        return '✗';
      case 'awaiting_approval':
        return '?';
      default:
        return '·';
    }
  };

  // Get status color class
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
      case 'starting':
      case 'streaming':
        return 'text-blue-400';
      case 'thinking':
        return 'text-purple-400';
      case 'completed':
        return 'text-green-400';
      case 'error':
        return 'text-red-400';
      case 'awaiting_approval':
        return 'text-yellow-400';
      default:
        return 'text-gray-500';
    }
  };

  // Format agent name for terminal display
  const formatAgentName = (name: string) => {
    return name.replace(/Agent$/, '').toLowerCase();
  };

  // Convert live outputs to sorted array
  const sortedLiveOutputs = Array.from(liveOutputs.values())
    .sort((a, b) => a.timestamp - b.timestamp);

  return (
    <div className="font-mono text-xs bg-gray-950 text-gray-300 p-3 rounded-lg border border-gray-800 min-h-[200px] max-h-[60vh] overflow-y-auto">
      {/* Terminal prompt style header */}
      <div className="text-gray-600 mb-2">
        $ workflow execute --stream
      </div>

      {/* No output yet */}
      {updates.length === 0 && !isRunning && (
        <div className="text-gray-600 italic">
          No output yet. Enter a task to begin.
        </div>
      )}

      {/* Live streaming output during workflow */}
      {isRunning && sortedLiveOutputs.length > 0 && (
        <div className="space-y-2">
          {sortedLiveOutputs.map((output) => (
            <div key={output.agentName} className="border-l-2 border-gray-800 pl-2">
              {/* Agent header line */}
              <div className="flex items-center gap-2">
                <span className={`${getStatusColor(output.status)}`}>
                  {getStatusIcon(output.status)}
                </span>
                <span className="text-gray-500">[{formatAgentName(output.agentName)}]</span>
                <span className="text-gray-400">{output.agentTitle}</span>
                {(output.status === 'running' || output.status === 'streaming') && (
                  <span className="animate-pulse text-blue-400">●</span>
                )}
              </div>
              {/* Agent output content */}
              {output.content && (
                <pre className="text-gray-400 whitespace-pre-wrap ml-4 mt-1">
                  {output.content.split('\n').map((line, i) => (
                    <div key={i} className="leading-relaxed">
                      {line.startsWith('✅') || line.startsWith('✓') ? (
                        <span className="text-green-400">{line}</span>
                      ) : line.startsWith('❌') || line.startsWith('⚠️') ? (
                        <span className="text-red-400">{line}</span>
                      ) : line.startsWith('$') || line.startsWith('>') ? (
                        <span className="text-blue-400">{line}</span>
                      ) : (
                        line
                      )}
                    </div>
                  ))}
                  {(output.status === 'running' || output.status === 'streaming') && (
                    <span className="inline-block w-1.5 h-3 bg-gray-400 animate-pulse" />
                  )}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Completed updates - shown as log entries */}
      {!isRunning && updates.length > 0 && (
        <div className="space-y-3">
          {updates.map((update, index) => (
            <div key={`${update.agent}-${index}`} className="border-l-2 border-gray-800 pl-2">
              {/* Agent header line */}
              <div className="flex items-center gap-2">
                <span className={`${getStatusColor(update.status || 'completed')}`}>
                  {getStatusIcon(update.status || 'completed')}
                </span>
                <span className="text-gray-500">[{formatAgentName(update.agent)}]</span>
                <span className="text-gray-400">{update.message || update.agent}</span>
                {update.execution_time !== undefined && (
                  <span className="text-gray-600 ml-auto">{update.execution_time.toFixed(1)}s</span>
                )}
              </div>

              {/* Streaming content if available */}
              {update.streaming_content && (
                <pre className="text-gray-500 whitespace-pre-wrap ml-4 mt-1 text-[10px]">
                  {update.streaming_content}
                </pre>
              )}

              {/* Artifacts */}
              {update.artifacts && update.artifacts.length > 0 && (
                <div className="ml-4 mt-1">
                  <div className="text-gray-600 mb-1">files ({update.artifacts.length}):</div>
                  {update.artifacts.map((artifact, i) => (
                    <ArtifactViewer key={i} artifact={artifact} />
                  ))}
                </div>
              )}

              {/* Single artifact */}
              {update.artifact && (
                <div className="ml-4 mt-1">
                  <ArtifactViewer artifact={update.artifact} />
                </div>
              )}

              {/* Issues */}
              {update.issues && update.issues.length > 0 && (
                <div className="ml-4 mt-1 text-red-400">
                  {update.issues.map((issue, i) => (
                    <div key={i}>! {typeof issue === 'string' ? issue : issue.issue}</div>
                  ))}
                </div>
              )}

              {/* Suggestions */}
              {update.suggestions && update.suggestions.length > 0 && (
                <div className="ml-4 mt-1 text-yellow-400">
                  {update.suggestions.map((sug, i) => (
                    <div key={i}>* {typeof sug === 'string' ? sug : sug.suggestion}</div>
                  ))}
                </div>
              )}
            </div>
          ))}

          {/* Workflow complete indicator */}
          <div className="text-green-400 mt-2">
            ✓ workflow completed
          </div>
        </div>
      )}

      {/* Running indicator at bottom */}
      {isRunning && (
        <div className="mt-3 flex items-center gap-2 text-gray-500">
          <span className="animate-spin">⟳</span>
          <span>running...</span>
        </div>
      )}
    </div>
  );
};

export default TerminalOutput;
