/**
 * AgentSpawnViewer component - Shows agent spawn events
 */
import { AgentSpawnInfo } from '../types/api';

interface AgentSpawnViewerProps {
  spawnInfo: AgentSpawnInfo;
}

const AgentSpawnViewer = ({ spawnInfo }: AgentSpawnViewerProps) => {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getAgentColor = (agentType: string) => {
    switch (agentType) {
      case 'PlanningAgent':
        return { bg: '#DA775620', border: '#DA7756', text: '#DA7756' };
      case 'CodingAgent':
        return { bg: '#16A34A20', border: '#16A34A', text: '#16A34A' };
      case 'ReviewAgent':
        return { bg: '#2563EB20', border: '#2563EB', text: '#2563EB' };
      default:
        return { bg: '#7C3AED20', border: '#7C3AED', text: '#7C3AED' };
    }
  };

  const colors = getAgentColor(spawnInfo.agent_type);

  return (
    <div
      className="flex items-start gap-3 p-3 rounded-xl border"
      style={{ backgroundColor: colors.bg, borderColor: colors.border }}
    >
      {/* Spawn icon */}
      <div
        className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
        style={{ backgroundColor: colors.border }}
      >
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
        </svg>
      </div>

      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold" style={{ color: colors.text }}>
            {spawnInfo.agent_type}
          </span>
          <span className="text-xs text-[#999999] font-mono">
            {spawnInfo.agent_id}
          </span>
        </div>

        {/* Spawn reason */}
        <p className="text-sm text-[#666666] mb-2">
          {spawnInfo.spawn_reason}
        </p>

        {/* Meta info */}
        <div className="flex items-center gap-4 text-xs text-[#999999]">
          {spawnInfo.parent_agent && (
            <div className="flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
              </svg>
              <span>Parent: {spawnInfo.parent_agent}</span>
            </div>
          )}
          <div className="flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{formatTime(spawnInfo.timestamp)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentSpawnViewer;
