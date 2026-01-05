/**
 * SharedContextViewer - Displays shared context between parallel agents
 * Dark theme for consistency with Claude Code style
 */
import { useState } from 'react';

interface ContextEntry {
  agent_id: string;
  agent_type: string;
  key: string;
  value_preview: string;
  description: string;
  timestamp: string;
}

interface AccessLogEntry {
  action: 'set' | 'get';
  agent_id?: string;
  requesting_agent?: string;
  source_agent?: string;
  agent_type?: string;
  key: string;
  timestamp: string;
}

interface SharedContextData {
  entries: ContextEntry[];
  access_log: AccessLogEntry[];
}

interface SharedContextViewerProps {
  data: SharedContextData | null;
  isVisible: boolean;
  onClose: () => void;
}

const SharedContextViewer = ({ data, isVisible, onClose }: SharedContextViewerProps) => {
  const [activeTab, setActiveTab] = useState<'entries' | 'log'>('entries');
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null);

  if (!isVisible || !data) return null;

  const getAgentColor = (agentType: string) => {
    const colors: Record<string, string> = {
      'CodingAgent': 'bg-green-900/50 text-green-400 border-green-700',
      'PlanningAgent': 'bg-orange-900/50 text-orange-400 border-orange-700',
      'ReviewAgent': 'bg-blue-900/50 text-blue-400 border-blue-700',
      'Orchestrator': 'bg-purple-900/50 text-purple-400 border-purple-700',
    };
    return colors[agentType] || 'bg-gray-800 text-gray-400 border-gray-700';
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg shadow-xl w-[800px] max-w-full max-h-[80vh] flex flex-col border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-purple-600 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
              </svg>
            </div>
            <div>
              <h2 className="text-sm font-medium text-gray-100">Shared Context</h2>
              <p className="text-xs text-gray-500">
                {data.entries.length} entries · {data.access_log.length} ops
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-gray-800 transition-colors text-gray-500 hover:text-gray-300"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700">
          <button
            onClick={() => setActiveTab('entries')}
            className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'entries'
                ? 'border-purple-500 text-purple-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            Entries ({data.entries.length})
          </button>
          <button
            onClick={() => setActiveTab('log')}
            className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'log'
                ? 'border-purple-500 text-purple-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            Log ({data.access_log.length})
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-3">
          {activeTab === 'entries' ? (
            <div className="space-y-2">
              {data.entries.length === 0 ? (
                <div className="text-center py-6 text-gray-600 text-sm">
                  No shared context entries
                </div>
              ) : (
                data.entries.map((entry, idx) => (
                  <div
                    key={idx}
                    className="border border-gray-800 rounded overflow-hidden"
                  >
                    <div
                      className="flex items-center justify-between p-2 bg-gray-800/50 cursor-pointer hover:bg-gray-800"
                      onClick={() => setExpandedEntry(expandedEntry === entry.key ? null : entry.key)}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded border ${getAgentColor(entry.agent_type)}`}>
                          {entry.agent_type.replace('Agent', '')}
                        </span>
                        <span className="font-mono text-xs text-gray-400">{entry.key}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-gray-600">
                          {new Date(entry.timestamp).toLocaleTimeString()}
                        </span>
                        <svg
                          className={`w-3 h-3 text-gray-600 transition-transform ${expandedEntry === entry.key ? 'rotate-180' : ''}`}
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth={1.5}
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                        </svg>
                      </div>
                    </div>
                    {expandedEntry === entry.key && (
                      <div className="p-2 border-t border-gray-800 bg-gray-900/50">
                        <div className="text-[10px] text-gray-600 mb-1">
                          <span className="text-gray-500">agent:</span> {entry.agent_id}
                        </div>
                        {entry.description && (
                          <div className="text-[10px] text-gray-600 mb-1">
                            <span className="text-gray-500">desc:</span> {entry.description}
                          </div>
                        )}
                        <pre className="text-xs font-mono bg-gray-950 text-gray-400 p-2 rounded overflow-x-auto max-h-40 mt-1">
                          {entry.value_preview}
                        </pre>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="space-y-1 font-mono text-xs">
              {data.access_log.length === 0 ? (
                <div className="text-center py-6 text-gray-600">
                  No access log entries
                </div>
              ) : (
                data.access_log.map((log, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center gap-2 p-1.5 rounded ${
                      log.action === 'set' ? 'bg-green-900/20' : 'bg-blue-900/20'
                    }`}
                  >
                    <span className={`px-1 py-0.5 text-[10px] font-medium rounded ${
                      log.action === 'set'
                        ? 'bg-green-900/50 text-green-400'
                        : 'bg-blue-900/50 text-blue-400'
                    }`}>
                      {log.action}
                    </span>
                    <div className="flex-1 text-gray-400">
                      {log.action === 'set' ? (
                        <>
                          <span className="text-gray-300">{log.agent_id}</span>
                          {' → '}
                          <span className="text-purple-400">{log.key}</span>
                        </>
                      ) : (
                        <>
                          <span className="text-gray-300">{log.requesting_agent}</span>
                          {' ← '}
                          <span className="text-purple-400">{log.key}</span>
                          {' from '}
                          <span className="text-gray-300">{log.source_agent}</span>
                        </>
                      )}
                    </div>
                    <span className="text-[10px] text-gray-600">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-2 border-t border-gray-800">
          <p className="text-[10px] text-gray-600 text-center">
            Shared context enables agents to share data and reference outputs
          </p>
        </div>
      </div>
    </div>
  );
};

export default SharedContextViewer;
