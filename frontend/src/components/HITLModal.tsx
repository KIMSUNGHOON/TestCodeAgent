/**
 * HITLModal - Human-in-the-Loop Modal Component
 *
 * Supports 5 checkpoint types:
 * - approval: Simple approve/reject
 * - review: Review with feedback
 * - edit: Direct content editing
 * - choice: Select from options
 * - confirm: Confirmation for dangerous actions
 */

import { useState, useEffect } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

// Types
interface ChoiceOption {
  option_id: string;
  title: string;
  description: string;
  preview?: string;
  pros: string[];
  cons: string[];
  recommended: boolean;
}

interface HITLContent {
  code?: string;
  language?: string;
  filename?: string;
  workflow_plan?: Record<string, any>;
  options?: ChoiceOption[];
  original?: string;
  modified?: string;
  diff?: string;
  action_description?: string;
  risks?: string[];
  summary?: string;
  details?: Record<string, any>;
}

interface HITLRequest {
  request_id: string;
  workflow_id: string;
  stage_id: string;
  agent_id?: string;
  checkpoint_type: 'approval' | 'review' | 'edit' | 'choice' | 'confirm';
  title: string;
  description: string;
  content: HITLContent;
  allow_skip?: boolean;
  priority: string;
  created_at: string;
}

interface HITLModalProps {
  request: HITLRequest;
  isOpen?: boolean;  // Optional - modal shown when request exists and isOpen is true/undefined
  onClose?: () => void;  // Alias for onCancel, called when modal is closed
  onApprove: (feedback?: string) => void;
  onReject: (reason: string) => void;
  onEdit: (modifiedContent: string, feedback?: string) => void;
  onRetry: (instructions: string) => void;
  onSelect: (optionId: string, feedback?: string) => void;
  onConfirm: (feedback?: string) => void;
  onCancel?: () => void;  // Made optional since onClose is preferred
}

const HITLModal = ({
  request,
  isOpen = true,  // Default to true if not provided
  onClose,
  onApprove,
  onReject,
  onEdit,
  onRetry,
  onSelect,
  onConfirm,
  onCancel,
}: HITLModalProps) => {
  // Use onClose if provided, otherwise fall back to onCancel
  const handleClose = onClose || onCancel || (() => {});

  // State hooks must be called before any early returns
  const [feedback, setFeedback] = useState('');
  const [editedContent, setEditedContent] = useState(request.content.code || '');
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  // Reset state when request changes
  useEffect(() => {
    setFeedback('');
    setEditedContent(request.content.code || '');
    setSelectedOption(null);
    setIsEditing(false);
  }, [request.request_id]);

  // Don't render if not open
  if (!isOpen) return null;

  const renderContent = () => {
    switch (request.checkpoint_type) {
      case 'approval':
        return <ApprovalView request={request} />;
      case 'review':
        return (
          <ReviewView
            request={request}
            isEditing={isEditing}
            editedContent={editedContent}
            onEditedContentChange={setEditedContent}
          />
        );
      case 'edit':
        return (
          <EditView
            request={request}
            editedContent={editedContent}
            onEditedContentChange={setEditedContent}
          />
        );
      case 'choice':
        return (
          <ChoiceView
            request={request}
            selectedOption={selectedOption}
            onOptionSelect={setSelectedOption}
          />
        );
      case 'confirm':
        return <ConfirmView request={request} />;
      default:
        return <ApprovalView request={request} />;
    }
  };

  const renderActions = () => {
    switch (request.checkpoint_type) {
      case 'approval':
        return (
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={() => onApprove(feedback || undefined)}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl bg-[#16A34A] hover:bg-[#15803D] text-white font-medium transition-colors flex items-center justify-center gap-2"
            >
              <CheckIcon />
              Approve
            </button>
            <button
              onClick={() => onReject(feedback || 'Rejected by user')}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl bg-[#DC2626] hover:bg-[#B91C1C] text-white font-medium transition-colors flex items-center justify-center gap-2"
            >
              <XIcon />
              Reject
            </button>
            <button
              onClick={handleClose}
              className="px-6 py-3 rounded-xl border border-[#E5E5E5] hover:bg-[#F5F4F2] text-[#666666] font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        );

      case 'review':
        return (
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={() => {
                if (isEditing) {
                  onEdit(editedContent, feedback || undefined);
                } else {
                  onApprove(feedback || undefined);
                }
              }}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl bg-[#16A34A] hover:bg-[#15803D] text-white font-medium transition-colors flex items-center justify-center gap-2"
            >
              <CheckIcon />
              {isEditing ? 'Save & Approve' : 'Approve'}
            </button>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className={`flex-1 sm:flex-none px-6 py-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2 ${
                isEditing
                  ? 'bg-[#F59E0B] hover:bg-[#D97706] text-white'
                  : 'bg-[#3B82F6] hover:bg-[#2563EB] text-white'
              }`}
            >
              <EditIcon />
              {isEditing ? 'Cancel Edit' : 'Edit'}
            </button>
            <button
              onClick={() => onRetry(feedback || 'Please try again')}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl bg-[#8B5CF6] hover:bg-[#7C3AED] text-white font-medium transition-colors flex items-center justify-center gap-2"
            >
              <RetryIcon />
              Retry
            </button>
            <button
              onClick={() => onReject(feedback || 'Rejected by user')}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl bg-[#DC2626] hover:bg-[#B91C1C] text-white font-medium transition-colors flex items-center justify-center gap-2"
            >
              <XIcon />
              Reject
            </button>
          </div>
        );

      case 'edit':
        return (
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={() => onEdit(editedContent, feedback || undefined)}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl bg-[#16A34A] hover:bg-[#15803D] text-white font-medium transition-colors flex items-center justify-center gap-2"
            >
              <CheckIcon />
              Save Changes
            </button>
            <button
              onClick={() => setEditedContent(request.content.code || request.content.original || '')}
              className="px-6 py-3 rounded-xl border border-[#E5E5E5] hover:bg-[#F5F4F2] text-[#666666] font-medium transition-colors"
            >
              Reset
            </button>
            <button
              onClick={handleClose}
              className="px-6 py-3 rounded-xl border border-[#E5E5E5] hover:bg-[#F5F4F2] text-[#666666] font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        );

      case 'choice':
        return (
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={() => selectedOption && onSelect(selectedOption, feedback || undefined)}
              disabled={!selectedOption}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl bg-[#16A34A] hover:bg-[#15803D] disabled:bg-[#E5E5E5] disabled:cursor-not-allowed text-white font-medium transition-colors flex items-center justify-center gap-2"
            >
              <CheckIcon />
              Confirm Selection
            </button>
            <button
              onClick={handleClose}
              className="px-6 py-3 rounded-xl border border-[#E5E5E5] hover:bg-[#F5F4F2] text-[#666666] font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        );

      case 'confirm':
        return (
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={() => onConfirm(feedback || undefined)}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl bg-[#DC2626] hover:bg-[#B91C1C] text-white font-medium transition-colors flex items-center justify-center gap-2"
            >
              <AlertIcon />
              Yes, Proceed
            </button>
            <button
              onClick={handleClose}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl bg-[#16A34A] hover:bg-[#15803D] text-white font-medium transition-colors flex items-center justify-center gap-2"
            >
              <XIcon />
              No, Cancel
            </button>
          </div>
        );

      default:
        return null;
    }
  };

  const getPriorityStyles = () => {
    switch (request.priority) {
      case 'critical':
        return 'border-red-500 bg-red-50';
      case 'high':
        return 'border-orange-500 bg-orange-50';
      default:
        return 'border-[#E5E5E5] bg-white';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className={`w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-2xl shadow-2xl border-2 ${getPriorityStyles()} flex flex-col animate-in fade-in zoom-in duration-200`}>
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E5E5E5] bg-white">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${getCheckpointIcon(request.checkpoint_type).bgColor}`}>
                {getCheckpointIcon(request.checkpoint_type).icon}
              </div>
              <div>
                <h2 className="text-xl font-semibold text-[#1A1A1A]">{request.title}</h2>
                <p className="text-sm text-[#666666] mt-1">{request.description}</p>
                <div className="flex items-center gap-2 mt-2 text-xs text-[#999999]">
                  <span className="bg-[#F5F4F2] px-2 py-1 rounded">{request.checkpoint_type.toUpperCase()}</span>
                  {request.agent_id && (
                    <span className="bg-[#F5F4F2] px-2 py-1 rounded">Agent: {request.agent_id}</span>
                  )}
                  <span className="bg-[#F5F4F2] px-2 py-1 rounded">Stage: {request.stage_id}</span>
                </div>
              </div>
            </div>
            <button
              onClick={handleClose}
              className="p-2 rounded-lg hover:bg-[#F5F4F2] text-[#666666] transition-colors"
            >
              <XIcon />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-[#FAF9F7]">
          {renderContent()}

          {/* Feedback Input */}
          {request.checkpoint_type !== 'choice' && (
            <div className="mt-6">
              <label className="block text-sm font-medium text-[#666666] mb-2">
                Feedback (optional)
              </label>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Add any comments or instructions..."
                className="w-full px-4 py-3 bg-white text-[#1A1A1A] placeholder-[#999999] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#DA7756] border border-[#E5E5E5] resize-none"
                rows={3}
              />
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t border-[#E5E5E5] bg-white">
          {renderActions()}
        </div>
      </div>
    </div>
  );
};

// Sub-components for different checkpoint types

const ApprovalView = ({ request }: { request: HITLRequest }) => {
  const { content } = request;

  return (
    <div className="space-y-4">
      {content.summary && (
        <div className="bg-white rounded-xl p-4 border border-[#E5E5E5]">
          <h3 className="text-sm font-medium text-[#666666] mb-2">Summary</h3>
          <p className="text-[#1A1A1A]">{content.summary}</p>
        </div>
      )}

      {content.workflow_plan && (
        <div className="bg-white rounded-xl p-4 border border-[#E5E5E5]">
          <h3 className="text-sm font-medium text-[#666666] mb-2">Workflow Plan</h3>
          <WorkflowPlanPreview plan={content.workflow_plan} />
        </div>
      )}

      {content.details?.artifacts && (
        <div className="bg-white rounded-xl p-4 border border-[#E5E5E5]">
          <h3 className="text-sm font-medium text-[#666666] mb-2">
            Generated Artifacts ({content.details.artifacts.length})
          </h3>
          <div className="space-y-2">
            {content.details.artifacts.map((artifact: any, idx: number) => (
              <div key={idx} className="flex items-center gap-2 text-sm">
                <span className="text-[#DA7756]">{artifact.filename || artifact.file_path}</span>
                <span className="text-[#999999]">({artifact.language})</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const ReviewView = ({
  request,
  isEditing,
  editedContent,
  onEditedContentChange,
}: {
  request: HITLRequest;
  isEditing: boolean;
  editedContent: string;
  onEditedContentChange: (content: string) => void;
}) => {
  const { content } = request;

  return (
    <div className="space-y-4">
      {content.summary && (
        <div className="bg-white rounded-xl p-4 border border-[#E5E5E5]">
          <p className="text-[#1A1A1A]">{content.summary}</p>
        </div>
      )}

      {content.code && (
        <div className="bg-white rounded-xl border border-[#E5E5E5] overflow-hidden">
          <div className="px-4 py-2 bg-[#1E1E1E] text-white flex items-center justify-between">
            <span className="text-sm font-mono">{content.filename || 'code'}</span>
            <span className="text-xs text-[#999999]">{content.language}</span>
          </div>
          {isEditing ? (
            <textarea
              value={editedContent}
              onChange={(e) => onEditedContentChange(e.target.value)}
              className="w-full p-4 font-mono text-sm bg-[#1E1E1E] text-[#D4D4D4] focus:outline-none resize-none"
              style={{ minHeight: '300px' }}
            />
          ) : (
            <SyntaxHighlighter
              language={content.language || 'python'}
              style={oneDark}
              customStyle={{ margin: 0, borderRadius: 0 }}
            >
              {content.code}
            </SyntaxHighlighter>
          )}
        </div>
      )}

      {content.details?.artifacts && content.details.artifacts.length > 1 && (
        <div className="bg-white rounded-xl p-4 border border-[#E5E5E5]">
          <h3 className="text-sm font-medium text-[#666666] mb-2">
            Additional Files ({content.details.artifacts.length - 1})
          </h3>
          <div className="space-y-2">
            {content.details.artifacts.slice(1).map((artifact: any, idx: number) => (
              <div key={idx} className="flex items-center gap-2 text-sm">
                <span className="text-[#DA7756]">{artifact.filename || artifact.file_path}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const EditView = ({
  request,
  editedContent,
  onEditedContentChange,
}: {
  request: HITLRequest;
  editedContent: string;
  onEditedContentChange: (content: string) => void;
}) => {
  const { content } = request;

  return (
    <div className="space-y-4">
      {content.summary && (
        <div className="bg-white rounded-xl p-4 border border-[#E5E5E5]">
          <p className="text-[#1A1A1A]">{content.summary}</p>
        </div>
      )}

      <div className="bg-white rounded-xl border border-[#E5E5E5] overflow-hidden">
        <div className="px-4 py-2 bg-[#1E1E1E] text-white flex items-center justify-between">
          <span className="text-sm font-mono">{content.filename || 'Edit Content'}</span>
          <span className="text-xs text-[#F59E0B]">Editing Mode</span>
        </div>
        <textarea
          value={editedContent}
          onChange={(e) => onEditedContentChange(e.target.value)}
          className="w-full p-4 font-mono text-sm bg-[#1E1E1E] text-[#D4D4D4] focus:outline-none resize-none"
          style={{ minHeight: '400px' }}
        />
      </div>

      {content.diff && (
        <div className="bg-white rounded-xl p-4 border border-[#E5E5E5]">
          <h3 className="text-sm font-medium text-[#666666] mb-2">Original Diff</h3>
          <pre className="text-xs font-mono bg-[#1E1E1E] text-[#D4D4D4] p-3 rounded-lg overflow-x-auto">
            {content.diff}
          </pre>
        </div>
      )}
    </div>
  );
};

const ChoiceView = ({
  request,
  selectedOption,
  onOptionSelect,
}: {
  request: HITLRequest;
  selectedOption: string | null;
  onOptionSelect: (id: string) => void;
}) => {
  const { content } = request;

  return (
    <div className="space-y-4">
      {content.summary && (
        <div className="bg-white rounded-xl p-4 border border-[#E5E5E5]">
          <p className="text-[#1A1A1A]">{content.summary}</p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {content.options?.map((option) => (
          <button
            key={option.option_id}
            onClick={() => onOptionSelect(option.option_id)}
            className={`text-left p-4 rounded-xl border-2 transition-all ${
              selectedOption === option.option_id
                ? 'border-[#16A34A] bg-[#F0FDF4]'
                : 'border-[#E5E5E5] bg-white hover:border-[#DA7756]'
            }`}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <h4 className="font-medium text-[#1A1A1A]">{option.title}</h4>
              {option.recommended && (
                <span className="px-2 py-0.5 text-xs bg-[#16A34A] text-white rounded-full">
                  Recommended
                </span>
              )}
            </div>
            <p className="text-sm text-[#666666] mb-3">{option.description}</p>

            {(option.pros.length > 0 || option.cons.length > 0) && (
              <div className="space-y-2 text-xs">
                {option.pros.length > 0 && (
                  <div>
                    <span className="text-[#16A34A] font-medium">Pros:</span>
                    <ul className="list-disc list-inside text-[#666666]">
                      {option.pros.map((pro, idx) => (
                        <li key={idx}>{pro}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {option.cons.length > 0 && (
                  <div>
                    <span className="text-[#DC2626] font-medium">Cons:</span>
                    <ul className="list-disc list-inside text-[#666666]">
                      {option.cons.map((con, idx) => (
                        <li key={idx}>{con}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {option.preview && (
              <div className="mt-3 p-2 bg-[#1E1E1E] rounded text-xs font-mono text-[#D4D4D4] overflow-x-auto">
                <pre>{option.preview}</pre>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};

const ConfirmView = ({ request }: { request: HITLRequest }) => {
  const { content } = request;

  return (
    <div className="space-y-4">
      <div className="bg-red-50 rounded-xl p-4 border border-red-200">
        <div className="flex items-start gap-3">
          <AlertIcon className="text-red-500 mt-0.5" />
          <div>
            <h3 className="font-medium text-red-800">Warning</h3>
            <p className="text-sm text-red-700 mt-1">
              {content.action_description || 'This action requires your confirmation.'}
            </p>
          </div>
        </div>
      </div>

      {content.risks && content.risks.length > 0 && (
        <div className="bg-white rounded-xl p-4 border border-[#E5E5E5]">
          <h3 className="text-sm font-medium text-[#666666] mb-2">Potential Risks</h3>
          <ul className="space-y-2">
            {content.risks.map((risk, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-[#1A1A1A]">
                <span className="text-red-500">•</span>
                {risk}
              </li>
            ))}
          </ul>
        </div>
      )}

      {content.summary && (
        <div className="bg-white rounded-xl p-4 border border-[#E5E5E5]">
          <p className="text-[#1A1A1A]">{content.summary}</p>
        </div>
      )}
    </div>
  );
};

const WorkflowPlanPreview = ({ plan }: { plan: Record<string, any> }) => {
  const stages = plan.stages || [];

  return (
    <div className="space-y-2">
      {stages.map((stage: any, idx: number) => (
        <div key={idx} className="flex items-center gap-3 p-2 bg-[#F5F4F2] rounded-lg">
          <div className="w-6 h-6 rounded-full bg-[#DA7756] text-white flex items-center justify-center text-xs font-medium">
            {idx + 1}
          </div>
          <div>
            <span className="font-medium text-[#1A1A1A]">{stage.name}</span>
            {stage.agents && (
              <span className="ml-2 text-xs text-[#666666]">
                ({stage.agents.join(', ')})
              </span>
            )}
          </div>
          {stage.hitl_required && (
            <span className="ml-auto text-xs bg-[#F59E0B] text-white px-2 py-0.5 rounded">
              HITL
            </span>
          )}
        </div>
      ))}
    </div>
  );
};

// Icons
const CheckIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
  </svg>
);

const XIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const EditIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
  </svg>
);

const RetryIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
  </svg>
);

const AlertIcon = ({ className = '' }: { className?: string }) => (
  <svg className={`w-5 h-5 ${className}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
  </svg>
);

const getCheckpointIcon = (type: string) => {
  switch (type) {
    case 'approval':
      return {
        icon: <CheckIcon />,
        bgColor: 'bg-[#16A34A] text-white',
      };
    case 'review':
      return {
        icon: (
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        ),
        bgColor: 'bg-[#3B82F6] text-white',
      };
    case 'edit':
      return {
        icon: <EditIcon />,
        bgColor: 'bg-[#F59E0B] text-white',
      };
    case 'choice':
      return {
        icon: (
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 15L12 18.75 15.75 15m-7.5-6L12 5.25 15.75 9" />
          </svg>
        ),
        bgColor: 'bg-[#8B5CF6] text-white',
      };
    case 'confirm':
      return {
        icon: <AlertIcon />,
        bgColor: 'bg-[#DC2626] text-white',
      };
    default:
      return {
        icon: <CheckIcon />,
        bgColor: 'bg-[#666666] text-white',
      };
  }
};

export default HITLModal;
