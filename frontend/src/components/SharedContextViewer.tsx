/**
 * SharedContextViewer - Displays shared context between parallel agents
 * Shows what data each agent contributed and accessed
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
      'CodingAgent': 'bg-green-100 text-green-800 border-green-300',
      'PlanningAgent': 'bg-orange-100 text-orange-800 border-orange-300',
      'ReviewAgent': 'bg-blue-100 text-blue-800 border-blue-300',
      'Orchestrator': 'bg-purple-100 text-purple-800 border-purple-300',
    };
    return colors[agentType] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-[800px] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Shared Context</h2>
              <p className="text-sm text-gray-500">
                {data.entries.length} entries · {data.access_log.length} operations
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab('entries')}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'entries'
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Context Entries ({data.entries.length})
          </button>
          <button
            onClick={() => setActiveTab('log')}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'log'
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Access Log ({data.access_log.length})
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'entries' ? (
            <div className="space-y-3">
              {data.entries.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No shared context entries yet
                </div>
              ) : (
                data.entries.map((entry, idx) => (
                  <div
                    key={idx}
                    className="border rounded-lg overflow-hidden"
                  >
                    <div
                      className="flex items-center justify-between p-3 bg-gray-50 cursor-pointer hover:bg-gray-100"
                      onClick={() => setExpandedEntry(expandedEntry === entry.key ? null : entry.key)}
                    >
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded border ${getAgentColor(entry.agent_type)}`}>
                          {entry.agent_type}
                        </span>
                        <span className="font-mono text-sm text-gray-700">{entry.key}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">
                          {new Date(entry.timestamp).toLocaleTimeString()}
                        </span>
                        <svg
                          className={`w-4 h-4 text-gray-400 transition-transform ${expandedEntry === entry.key ? 'rotate-180' : ''}`}
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
                      <div className="p-3 border-t bg-white">
                        <div className="text-xs text-gray-500 mb-2">
                          <strong>Agent ID:</strong> {entry.agent_id}
                        </div>
                        {entry.description && (
                          <div className="text-xs text-gray-500 mb-2">
                            <strong>Description:</strong> {entry.description}
                          </div>
                        )}
                        <div className="text-xs text-gray-500 mb-2">
                          <strong>Value Preview:</strong>
                        </div>
                        <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto max-h-48">
                          {entry.value_preview}
                        </pre>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="space-y-2">
              {data.access_log.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No access log entries yet
                </div>
              ) : (
                data.access_log.map((log, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center gap-3 p-2 rounded-lg ${
                      log.action === 'set' ? 'bg-green-50' : 'bg-blue-50'
                    }`}
                  >
                    <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                      log.action === 'set'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}>
                      {log.action.toUpperCase()}
                    </span>
                    <div className="flex-1 text-sm">
                      {log.action === 'set' ? (
                        <span>
                          <span className="font-medium">{log.agent_id}</span>
                          {' → '}
                          <span className="font-mono text-purple-600">{log.key}</span>
                        </span>
                      ) : (
                        <span>
                          <span className="font-medium">{log.requesting_agent}</span>
                          {' ← '}
                          <span className="font-mono text-purple-600">{log.key}</span>
                          {' from '}
                          <span className="font-medium">{log.source_agent}</span>
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50">
          <p className="text-xs text-gray-500 text-center">
            Shared context allows parallel agents to share information and reference each other's outputs
          </p>
        </div>
      </div>
    </div>
  );
};

export default SharedContextViewer;
