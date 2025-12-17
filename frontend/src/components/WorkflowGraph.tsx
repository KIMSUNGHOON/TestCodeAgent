/**
 * WorkflowGraph component - Simple workflow visualization with parallel support
 */
import { WorkflowInfo } from '../types/api';

interface WorkflowGraphProps {
  workflowInfo: WorkflowInfo;
  isRunning: boolean;
}

const WorkflowGraph = ({ workflowInfo, isRunning }: WorkflowGraphProps) => {
  const nodeColors: Record<string, string> = {
    PlanningAgent: '#DA7756',
    AnalysisAgent: '#EC4899',
    CodingAgent: '#16A34A',
    RefactorAgent: '#14B8A6',
    ReviewAgent: '#2563EB',
    FixCodeAgent: '#F59E0B',
    Decision: '#7C3AED'
  };

  const isNodeComplete = (node: string): boolean => {
    if (!workflowInfo.current_node) return false;
    if (workflowInfo.current_node === 'END') return true;
    const currentIdx = workflowInfo.nodes.indexOf(workflowInfo.current_node);
    const nodeIdx = workflowInfo.nodes.indexOf(node);
    return nodeIdx < currentIdx;
  };

  const isNodeCurrent = (node: string): boolean => {
    return workflowInfo.current_node === node;
  };

  return (
    <div className="mb-6 p-4 bg-white rounded-xl border border-[#7C3AED40] shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-[#7C3AED] animate-pulse' : 'bg-green-500'}`} />
          <span className="text-sm font-medium text-[#7C3AED]">{workflowInfo.workflow_type}</span>
        </div>
        <span className="text-xs text-[#999999]">
          {workflowInfo.current_node === 'END' ? 'Complete' : `Current: ${workflowInfo.current_node}`}
        </span>
      </div>
      <div className="flex items-center gap-1 overflow-x-auto py-2">
        {/* START */}
        <div className="px-2 py-1 rounded text-xs font-medium bg-[#1A1A1A] text-white flex-shrink-0">
          START
        </div>
        <svg className="w-4 h-4 text-[#999999] flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
        </svg>

        {/* Agent nodes */}
        {workflowInfo.nodes.map((node, idx) => {
          const isCurrent = isNodeCurrent(node);
          const color = nodeColors[node] || '#666666';
          const isComplete = isNodeComplete(node);

          return (
            <div key={node} className="flex items-center gap-1 flex-shrink-0">
              <div
                className="px-2 py-1 rounded text-xs font-medium flex items-center gap-1"
                style={{
                  backgroundColor: isCurrent || isComplete ? color : `${color}30`,
                  color: isCurrent || isComplete ? 'white' : color,
                  boxShadow: isCurrent ? `0 0 0 2px white, 0 0 0 4px ${color}` : undefined
                }}
              >
                {isComplete && (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                )}
                {isCurrent && <div className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />}
                {node.replace('Agent', '')}
              </div>
              {idx < workflowInfo.nodes.length - 1 && (
                <svg className="w-4 h-4 text-[#999999]" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              )}
            </div>
          );
        })}

        <svg className="w-4 h-4 text-[#999999] flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
        </svg>

        {/* END */}
        <div
          className={`px-2 py-1 rounded text-xs font-medium flex-shrink-0 ${
            workflowInfo.current_node === 'END' ? 'bg-[#16A34A] text-white ring-2 ring-[#16A34A] ring-offset-1' : 'bg-[#16A34A30] text-[#16A34A]'
          }`}
        >
          {workflowInfo.current_node === 'END' && (
            <svg className="w-3 h-3 inline mr-1" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          )}
          END
        </div>
      </div>
    </div>
  );
};

export default WorkflowGraph;
