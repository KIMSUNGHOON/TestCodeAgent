/**
 * WorkflowGraph component - Graph-based workflow visualization
 * Shows workflow nodes and edges with support for parallel execution
 */
import { WorkflowInfo } from '../types/api';

interface WorkflowGraphProps {
  workflowInfo: WorkflowInfo;
  isRunning: boolean;
}

const WorkflowGraph = ({ workflowInfo, isRunning }: WorkflowGraphProps) => {
  const nodeColors: Record<string, string> = {
    START: '#1A1A1A',
    PlanningAgent: '#DA7756',
    AnalysisAgent: '#EC4899',
    CodingAgent: '#16A34A',
    RefactorAgent: '#14B8A6',
    ReviewAgent: '#2563EB',
    FixCodeAgent: '#F59E0B',
    Decision: '#7C3AED',
    END: '#16A34A'
  };

  const getNodeColor = (node: string): string => {
    return nodeColors[node] || '#666666';
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

  // Build graph layout
  const allNodes = ['START', ...workflowInfo.nodes, 'END'];

  // Detect parallel branches by analyzing edges
  const hasParallelExecution = workflowInfo.edges?.some(edge =>
    edge.condition?.includes('parallel')
  );

  return (
    <div className="mb-6 p-5 bg-white rounded-xl border border-[#7C3AED40] shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${isRunning ? 'bg-[#7C3AED] animate-pulse' : 'bg-green-500'}`} />
          <span className="text-sm font-semibold text-[#1A1A1A]">{workflowInfo.workflow_type}</span>
          {hasParallelExecution && (
            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full border border-purple-200">
              Parallel
            </span>
          )}
        </div>
        <span className="text-xs text-[#999999]">
          {workflowInfo.current_node === 'END' ? '✓ Complete' : `⚡ ${workflowInfo.current_node}`}
        </span>
      </div>

      {/* Graph Visualization */}
      <div className="relative bg-gradient-to-br from-gray-50 to-white rounded-lg p-6 border border-gray-200">
        {/* Simple flow layout */}
        <div className="flex items-start justify-between gap-6">
          {allNodes.map((node, idx) => {
            const color = getNodeColor(node);
            const isCurrent = node === 'START' ? false : node === 'END' ? workflowInfo.current_node === 'END' : isNodeCurrent(node);
            const isComplete = node === 'START' ? true : node === 'END' ? workflowInfo.current_node === 'END' : isNodeComplete(node);
            const displayName = node === 'START' || node === 'END' ? node : node.replace('Agent', '');

            return (
              <div key={node} className="flex flex-col items-center flex-1 min-w-0">
                {/* Node */}
                <div className="relative">
                  <div
                    className={`
                      px-4 py-3 rounded-lg font-medium text-sm text-center shadow-md
                      transition-all duration-300 min-w-[100px]
                      ${isCurrent ? 'ring-4 ring-offset-2 scale-110' : ''}
                      ${isComplete && !isCurrent ? 'shadow-sm' : ''}
                    `}
                    style={{
                      backgroundColor: isCurrent || isComplete ? color : `${color}20`,
                      color: isCurrent || isComplete ? 'white' : color,
                      borderColor: color,
                      borderWidth: '2px',
                      borderStyle: 'solid'
                    }}
                  >
                    {/* Status indicator */}
                    <div className="flex items-center justify-center gap-2 mb-1">
                      {isComplete && !isCurrent && (
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      )}
                      {isCurrent && (
                        <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                      )}
                    </div>

                    {/* Node name */}
                    <div className="font-semibold">{displayName}</div>

                    {/* Node type icon */}
                    <div className="text-xs opacity-75 mt-1">
                      {node === 'START' && '🎯'}
                      {node === 'PlanningAgent' && '📋'}
                      {node === 'CodingAgent' && '💻'}
                      {node === 'ReviewAgent' && '🔍'}
                      {node === 'FixCodeAgent' && '🔧'}
                      {node === 'Decision' && '⚖️'}
                      {node === 'END' && '✅'}
                    </div>
                  </div>

                  {/* Current node pulse effect */}
                  {isCurrent && (
                    <div
                      className="absolute inset-0 rounded-lg animate-ping opacity-20"
                      style={{ backgroundColor: color }}
                    />
                  )}
                </div>

                {/* Arrow to next node */}
                {idx < allNodes.length - 1 && (
                  <div className="absolute" style={{
                    left: '50%',
                    top: '50%',
                    transform: 'translate(50%, -50%)',
                    width: 'calc(100% / ' + allNodes.length + ' - 24px)',
                    zIndex: 0
                  }}>
                    <svg
                      className="w-full h-8"
                      viewBox="0 0 100 20"
                      preserveAspectRatio="none"
                      style={{
                        stroke: isComplete ? color : '#E5E5E5',
                        strokeWidth: 2,
                        fill: 'none'
                      }}
                    >
                      <defs>
                        <marker
                          id={`arrow-${idx}`}
                          markerWidth="10"
                          markerHeight="10"
                          refX="8"
                          refY="3"
                          orient="auto"
                          markerUnits="strokeWidth"
                        >
                          <path d="M0,0 L0,6 L9,3 z" fill={isComplete ? color : '#E5E5E5'} />
                        </marker>
                      </defs>
                      <line
                        x1="0"
                        y1="10"
                        x2="100"
                        y2="10"
                        markerEnd={`url(#arrow-${idx})`}
                      />
                    </svg>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Workflow metadata */}
        <div className="mt-6 pt-4 border-t border-gray-200 flex items-center justify-between text-xs">
          <div className="flex items-center gap-4 text-gray-600">
            <span>📊 {workflowInfo.nodes.length} stages</span>
            {workflowInfo.max_iterations && (
              <span>🔄 Max {workflowInfo.max_iterations} iterations</span>
            )}
            {workflowInfo.dynamically_created && (
              <span className="text-purple-600">⚡ Dynamic workflow</span>
            )}
          </div>
          <div className="text-gray-500">
            {workflowInfo.workflow_id.slice(0, 8)}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkflowGraph;
