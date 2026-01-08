/**
 * PlanApprovalModal - Plan Mode Approval Component (Phase 5)
 * Displays execution plans for user review and approval
 */

import { useState } from 'react';

// Types
interface PlanStep {
  step: number;
  action: string;
  target: string;
  description: string;
  requires_approval: boolean;
  estimated_complexity: string;
  dependencies: number[];
  status: string;
}

interface ExecutionPlan {
  plan_id: string;
  session_id: string;
  created_at: string;
  user_request: string;
  steps: PlanStep[];
  estimated_files: string[];
  risks: string[];
  total_steps: number;
  approval_status: string;
}

interface PlanApprovalModalProps {
  plan: ExecutionPlan;
  isOpen: boolean;
  onClose: () => void;
  onApprove: () => void;
  onReject: (reason: string) => void;
  onModify: (steps: PlanStep[]) => void;
}

const PlanApprovalModal = ({
  plan,
  isOpen,
  onClose,
  onApprove,
  onReject,
  onModify,
}: PlanApprovalModalProps) => {
  const [steps, setSteps] = useState<PlanStep[]>(plan.steps);
  const [isEditing, setIsEditing] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);

  if (!isOpen) return null;

  const handleStepToggle = (stepNum: number, field: 'requires_approval') => {
    setSteps(prev =>
      prev.map(s =>
        s.step === stepNum ? { ...s, [field]: !s[field] } : s
      )
    );
  };

  const handleApprove = () => {
    if (isEditing) {
      onModify(steps);
    }
    onApprove();
  };

  const handleReject = () => {
    if (showRejectInput && rejectReason.trim()) {
      onReject(rejectReason);
    } else {
      setShowRejectInput(true);
    }
  };

  const getComplexityIcon = (complexity: string) => {
    switch (complexity) {
      case 'low': return { icon: 'circle', color: 'text-green-400', bg: 'bg-green-400' };
      case 'medium': return { icon: 'circle', color: 'text-yellow-400', bg: 'bg-yellow-400' };
      case 'high': return { icon: 'circle', color: 'text-red-400', bg: 'bg-red-400' };
      default: return { icon: 'circle', color: 'text-gray-400', bg: 'bg-gray-400' };
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'create_file': return '+';
      case 'modify_file': return '~';
      case 'delete_file': return '-';
      case 'run_tests': return 'T';
      case 'run_lint': return 'L';
      case 'install_deps': return 'D';
      case 'review_code': return 'R';
      case 'refactor': return 'F';
      default: return '*';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'create_file': return 'text-green-400 bg-green-900/30';
      case 'modify_file': return 'text-yellow-400 bg-yellow-900/30';
      case 'delete_file': return 'text-red-400 bg-red-900/30';
      case 'run_tests': return 'text-blue-400 bg-blue-900/30';
      case 'run_lint': return 'text-purple-400 bg-purple-900/30';
      default: return 'text-gray-400 bg-gray-900/30';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-lg shadow-2xl border border-gray-700 bg-gray-900 flex flex-col">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-700 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-blue-600 text-white">
              <PlanIcon />
            </div>
            <div>
              <h2 className="text-lg font-medium text-gray-100">Execution Plan Review</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {plan.total_steps} steps | {plan.estimated_files.length} files
              </p>
              <div className="flex items-center gap-1.5 mt-1.5">
                <span className="text-[10px] px-1.5 py-0.5 bg-blue-900 text-blue-300 rounded font-mono">
                  {plan.plan_id}
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  plan.approval_status === 'pending' ? 'bg-yellow-900 text-yellow-300' :
                  plan.approval_status === 'approved' ? 'bg-green-900 text-green-300' :
                  'bg-red-900 text-red-300'
                }`}>
                  {plan.approval_status}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-gray-800 text-gray-500 hover:text-gray-300"
          >
            <XIcon />
          </button>
        </div>

        {/* Request Summary */}
        <div className="px-4 py-3 bg-gray-800/50 border-b border-gray-700">
          <p className="text-xs text-gray-500 mb-1">Original Request:</p>
          <p className="text-sm text-gray-300">{plan.user_request}</p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 bg-gray-950">
          {/* Steps */}
          <div className="space-y-2 mb-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-300">Execution Steps</h3>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className={`text-xs px-2 py-1 rounded ${
                  isEditing ? 'bg-amber-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-300'
                }`}
              >
                {isEditing ? 'Done Editing' : 'Edit Steps'}
              </button>
            </div>

            {steps.map((step, idx) => {
              const complexity = getComplexityIcon(step.estimated_complexity);
              const actionColor = getActionColor(step.action);

              return (
                <div
                  key={step.step}
                  className={`rounded-lg border ${
                    step.requires_approval ? 'border-amber-700 bg-amber-900/10' : 'border-gray-800 bg-gray-800/30'
                  } p-3 transition-all hover:bg-gray-800/50`}
                >
                  <div className="flex items-start gap-3">
                    {/* Step Number */}
                    <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center text-sm font-mono text-gray-400">
                      {step.step}
                    </div>

                    {/* Step Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${actionColor}`}>
                          {getActionIcon(step.action)} {step.action}
                        </span>
                        <span className="text-xs text-gray-500 font-mono truncate">
                          {step.target}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300">{step.description}</p>

                      <div className="flex items-center gap-3 mt-2">
                        {/* Complexity */}
                        <div className="flex items-center gap-1">
                          <div className={`w-2 h-2 rounded-full ${complexity.bg}`} />
                          <span className="text-[10px] text-gray-500">{step.estimated_complexity}</span>
                        </div>

                        {/* Dependencies */}
                        {step.dependencies.length > 0 && (
                          <span className="text-[10px] text-gray-600">
                            deps: {step.dependencies.join(', ')}
                          </span>
                        )}

                        {/* Approval Toggle (when editing) */}
                        {isEditing && (
                          <button
                            onClick={() => handleStepToggle(step.step, 'requires_approval')}
                            className={`text-[10px] px-2 py-0.5 rounded ${
                              step.requires_approval
                                ? 'bg-amber-600 text-white'
                                : 'bg-gray-700 text-gray-400'
                            }`}
                          >
                            {step.requires_approval ? 'Approval Required' : 'Auto'}
                          </button>
                        )}

                        {/* Approval Badge (when not editing) */}
                        {!isEditing && step.requires_approval && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-900/50 text-amber-400">
                            Approval Required
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Estimated Files */}
          {plan.estimated_files.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-300 mb-2">Affected Files</h3>
              <div className="flex flex-wrap gap-2">
                {plan.estimated_files.map((file, idx) => (
                  <span
                    key={idx}
                    className="text-xs font-mono px-2 py-1 bg-gray-800 text-gray-400 rounded"
                  >
                    {file}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Risks */}
          {plan.risks.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-red-400 mb-2 flex items-center gap-2">
                <AlertIcon /> Potential Risks
              </h3>
              <ul className="space-y-1">
                {plan.risks.map((risk, idx) => (
                  <li key={idx} className="text-xs text-gray-400 flex items-start gap-2">
                    <span className="text-red-400">*</span>
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Reject Reason Input */}
          {showRejectInput && (
            <div className="mt-4">
              <label className="block text-xs text-gray-500 mb-1">Rejection Reason</label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Please provide a reason for rejecting this plan..."
                className="w-full px-3 py-2 bg-gray-800 text-gray-200 placeholder-gray-600 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-red-500 border border-gray-700 resize-none"
                rows={2}
                autoFocus
              />
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-4 py-3 border-t border-gray-700 flex items-center gap-2 flex-wrap">
          <button
            onClick={handleApprove}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-green-600 hover:bg-green-500 text-white flex items-center gap-2"
          >
            <CheckIcon /> {isEditing ? 'Save & Approve' : 'Approve Plan'}
          </button>

          <button
            onClick={handleReject}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 hover:bg-red-500 text-white flex items-center gap-2"
          >
            <XIcon /> Reject
          </button>

          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-800 hover:bg-gray-700 text-gray-300"
          >
            Cancel
          </button>

          <div className="flex-1" />

          <span className="text-xs text-gray-600">
            Created: {new Date(plan.created_at).toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
};

// Icons
const PlanIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
  </svg>
);

const CheckIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
  </svg>
);

const XIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const AlertIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
  </svg>
);

export default PlanApprovalModal;
