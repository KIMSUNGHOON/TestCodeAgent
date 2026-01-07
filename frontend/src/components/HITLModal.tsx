/**
 * HITLModal - Human-in-the-Loop Modal Component
 * Dark theme for consistency with Claude Code style
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
  workflow_plan?: Record<string, unknown>;
  options?: ChoiceOption[];
  original?: string;
  modified?: string;
  diff?: string;
  action_description?: string;
  risks?: string[];
  summary?: string;
  details?: Record<string, unknown>;
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
  isOpen?: boolean;
  onClose?: () => void;
  onApprove: (feedback?: string) => void;
  onReject: (reason: string) => void;
  onEdit: (modifiedContent: string, feedback?: string) => void;
  onRetry: (instructions: string) => void;
  onSelect: (optionId: string, feedback?: string) => void;
  onConfirm: (feedback?: string) => void;
  onCancel?: () => void;
}

const HITLModal = ({
  request,
  isOpen = true,
  onClose,
  onApprove,
  onReject,
  onEdit,
  onRetry,
  onSelect,
  onConfirm,
  onCancel,
}: HITLModalProps) => {
  const handleClose = onClose || onCancel || (() => {});

  const [feedback, setFeedback] = useState('');
  const [editedContent, setEditedContent] = useState(request.content.code || '');
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    setFeedback('');
    setEditedContent(request.content.code || '');
    setSelectedOption(null);
    setIsEditing(false);
  }, [request.request_id]);

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
    const btnBase = "px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2";
    const btnPrimary = `${btnBase} bg-green-600 hover:bg-green-500 text-white`;
    const btnDanger = `${btnBase} bg-red-600 hover:bg-red-500 text-white`;
    const btnSecondary = `${btnBase} bg-gray-800 hover:bg-gray-700 text-gray-300`;
    const btnWarning = `${btnBase} bg-amber-600 hover:bg-amber-500 text-white`;
    const btnInfo = `${btnBase} bg-blue-600 hover:bg-blue-500 text-white`;

    switch (request.checkpoint_type) {
      case 'approval':
        return (
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={() => onApprove(feedback || undefined)} className={btnPrimary}>
              <CheckIcon /> Approve
            </button>
            <button onClick={() => onReject(feedback || 'Rejected')} className={btnDanger}>
              <XIcon /> Reject
            </button>
            <button onClick={handleClose} className={btnSecondary}>Cancel</button>
          </div>
        );

      case 'review':
        return (
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => isEditing ? onEdit(editedContent, feedback) : onApprove(feedback)}
              className={btnPrimary}
            >
              <CheckIcon /> {isEditing ? 'Save & Approve' : 'Approve'}
            </button>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className={isEditing ? btnWarning : btnInfo}
            >
              <EditIcon /> {isEditing ? 'Cancel Edit' : 'Edit'}
            </button>
            <button onClick={() => onRetry(feedback || 'Retry')} className={btnSecondary}>
              <RetryIcon /> Retry
            </button>
            <button onClick={() => onReject(feedback || 'Rejected')} className={btnDanger}>
              <XIcon /> Reject
            </button>
          </div>
        );

      case 'edit':
        return (
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={() => onEdit(editedContent, feedback)} className={btnPrimary}>
              <CheckIcon /> Save
            </button>
            <button
              onClick={() => setEditedContent(request.content.code || request.content.original || '')}
              className={btnSecondary}
            >
              Reset
            </button>
            <button onClick={handleClose} className={btnSecondary}>Cancel</button>
          </div>
        );

      case 'choice':
        return (
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => selectedOption && onSelect(selectedOption, feedback)}
              disabled={!selectedOption}
              className={`${btnPrimary} disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed`}
            >
              <CheckIcon /> Confirm
            </button>
            <button onClick={handleClose} className={btnSecondary}>Cancel</button>
          </div>
        );

      case 'confirm':
        return (
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={() => onConfirm(feedback)} className={btnDanger}>
              <AlertIcon /> Proceed
            </button>
            <button onClick={handleClose} className={btnPrimary}>
              <XIcon /> Cancel
            </button>
          </div>
        );

      default:
        return null;
    }
  };

  const getPriorityBorder = () => {
    switch (request.priority) {
      case 'critical': return 'border-red-500';
      case 'high': return 'border-orange-500';
      default: return 'border-gray-700';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className={`w-full max-w-3xl max-h-[85vh] overflow-hidden rounded-lg shadow-2xl border ${getPriorityBorder()} bg-gray-900 flex flex-col`}>
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-700 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${getCheckpointStyles(request.checkpoint_type)}`}>
              {getCheckpointIcon(request.checkpoint_type)}
            </div>
            <div>
              <h2 className="text-sm font-medium text-gray-100">{request.title}</h2>
              <p className="text-xs text-gray-500 mt-0.5">{request.description}</p>
              <div className="flex items-center gap-1.5 mt-1.5">
                <span className="text-[10px] px-1.5 py-0.5 bg-gray-800 text-gray-400 rounded">
                  {request.checkpoint_type}
                </span>
                {request.agent_id && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-gray-800 text-gray-400 rounded">
                    {request.agent_id}
                  </span>
                )}
              </div>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded hover:bg-gray-800 text-gray-500 hover:text-gray-300"
          >
            <XIcon />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 bg-gray-950">
          {renderContent()}

          {/* Feedback */}
          {request.checkpoint_type !== 'choice' && (
            <div className="mt-4">
              <label className="block text-xs text-gray-500 mb-1">Feedback (optional)</label>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Add comments..."
                className="w-full px-3 py-2 bg-gray-800 text-gray-200 placeholder-gray-600 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 border border-gray-700 resize-none"
                rows={2}
              />
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-4 py-3 border-t border-gray-700">
          {renderActions()}
        </div>
      </div>
    </div>
  );
};

// Sub-components

const ApprovalView = ({ request }: { request: HITLRequest }) => {
  const { content } = request;
  const details = content.details as {
    artifacts?: Array<{filename?: string; file_path?: string; language?: string; action?: string}>;
    security_findings?: Array<{severity?: string; category?: string; description?: string; file_path?: string; line_number?: number; recommendation?: string}>;
    qa_results?: Array<{test_name?: string; passed?: boolean; error?: string}>;
    review_issues?: string[];
    review_suggestions?: string[];
    quality_score?: number;
  } | undefined;

  const artifacts = details?.artifacts;
  const securityFindings = details?.security_findings || [];
  const qaResults = details?.qa_results || [];
  const reviewIssues = details?.review_issues || [];
  const reviewSuggestions = details?.review_suggestions || [];

  return (
    <div className="space-y-3">
      {/* Summary */}
      {content.summary && (
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
          <pre className="text-sm text-gray-300 whitespace-pre-wrap font-sans">{content.summary}</pre>
        </div>
      )}

      {/* Security Findings */}
      {securityFindings.length > 0 && (
        <div className="bg-red-900/20 rounded-lg p-3 border border-red-800/50">
          <h3 className="text-xs text-red-400 mb-2 font-medium">🔒 보안 이슈 ({securityFindings.length})</h3>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {securityFindings.map((f, i) => (
              <div key={i} className="text-xs bg-gray-900/50 rounded p-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                    f.severity === 'critical' ? 'bg-red-600 text-white' :
                    f.severity === 'high' ? 'bg-orange-600 text-white' :
                    f.severity === 'medium' ? 'bg-yellow-600 text-white' :
                    'bg-gray-600 text-white'
                  }`}>
                    {f.severity?.toUpperCase()}
                  </span>
                  <span className="text-gray-400">{f.category}</span>
                </div>
                <p className="text-gray-300">{f.description}</p>
                {f.file_path && (
                  <p className="text-gray-500 mt-1 font-mono">
                    📄 {f.file_path}{f.line_number ? `:${f.line_number}` : ''}
                  </p>
                )}
                {f.recommendation && (
                  <p className="text-green-400 mt-1 text-[10px]">💡 {f.recommendation}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* QA Results */}
      {qaResults.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
          <h3 className="text-xs text-gray-400 mb-2 font-medium">🧪 QA 테스트 결과</h3>
          <div className="space-y-1">
            {qaResults.map((t, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className={t.passed ? 'text-green-400' : 'text-red-400'}>
                  {t.passed ? '✓' : '✗'}
                </span>
                <span className="text-gray-300">{t.test_name}</span>
                {t.error && <span className="text-red-400 text-[10px]">({t.error})</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review Issues */}
      {reviewIssues.length > 0 && (
        <div className="bg-amber-900/20 rounded-lg p-3 border border-amber-800/50">
          <h3 className="text-xs text-amber-400 mb-2 font-medium">👀 리뷰 이슈 ({reviewIssues.length})</h3>
          <ul className="space-y-1">
            {reviewIssues.map((issue, i) => (
              <li key={i} className="text-xs text-gray-300 flex items-start gap-2">
                <span className="text-amber-400">•</span>
                {typeof issue === 'string' ? issue : (issue as {issue?: string}).issue}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Review Suggestions */}
      {reviewSuggestions.length > 0 && (
        <div className="bg-blue-900/20 rounded-lg p-3 border border-blue-800/50">
          <h3 className="text-xs text-blue-400 mb-2 font-medium">💡 개선 제안 ({reviewSuggestions.length})</h3>
          <ul className="space-y-1">
            {reviewSuggestions.map((sug, i) => (
              <li key={i} className="text-xs text-gray-300 flex items-start gap-2">
                <span className="text-blue-400">•</span>
                {typeof sug === 'string' ? sug : (sug as {suggestion?: string}).suggestion}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Workflow Plan */}
      {content.workflow_plan && (
        <WorkflowPlanPreview plan={content.workflow_plan} />
      )}

      {/* Artifacts */}
      {artifacts && artifacts.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
          <h3 className="text-xs text-gray-500 mb-2">📁 생성된 파일 ({artifacts.length})</h3>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {artifacts.map((a, i) => (
              <div key={i} className="text-xs font-mono text-gray-400 flex items-center gap-2">
                <span className={a.action === 'created' ? 'text-green-400' : 'text-yellow-400'}>
                  {a.action === 'created' ? '+' : '~'}
                </span>
                {a.filename || a.file_path}
                <span className="text-gray-600">[{a.language || 'unknown'}]</span>
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
  const details = content.details as {
    artifacts?: Array<{filename?: string; file_path?: string; language?: string; action?: string}>;
    security_findings?: Array<{severity?: string; category?: string; description?: string; file_path?: string; line_number?: number; recommendation?: string}>;
    qa_results?: Array<{test_name?: string; passed?: boolean; error?: string}>;
    review_issues?: string[];
    review_suggestions?: string[];
    quality_score?: number;
  } | undefined;

  const securityFindings = details?.security_findings || [];
  const reviewIssues = details?.review_issues || [];
  const reviewSuggestions = details?.review_suggestions || [];

  return (
    <div className="space-y-3">
      {/* Summary */}
      {content.summary && (
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
          <pre className="text-sm text-gray-300 whitespace-pre-wrap font-sans">{content.summary}</pre>
        </div>
      )}

      {/* Security Findings - Critical for Review */}
      {securityFindings.length > 0 && (
        <div className="bg-red-900/20 rounded-lg p-3 border border-red-800/50">
          <h3 className="text-xs text-red-400 mb-2 font-medium">🔒 보안 이슈 - 검토 필요 ({securityFindings.length})</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {securityFindings.map((f, i) => (
              <div key={i} className="text-xs bg-gray-900/50 rounded p-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                    f.severity === 'critical' ? 'bg-red-600 text-white' :
                    f.severity === 'high' ? 'bg-orange-600 text-white' :
                    f.severity === 'medium' ? 'bg-yellow-600 text-white' :
                    'bg-gray-600 text-white'
                  }`}>
                    {f.severity?.toUpperCase()}
                  </span>
                  <span className="text-gray-400">{f.category}</span>
                </div>
                <p className="text-gray-300">{f.description}</p>
                {f.file_path && (
                  <p className="text-gray-500 mt-1 font-mono text-[10px]">
                    📄 {f.file_path}{f.line_number ? `:${f.line_number}` : ''}
                  </p>
                )}
                {f.recommendation && (
                  <p className="text-green-400 mt-1 text-[10px]">💡 권장: {f.recommendation}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review Issues */}
      {reviewIssues.length > 0 && (
        <div className="bg-amber-900/20 rounded-lg p-3 border border-amber-800/50">
          <h3 className="text-xs text-amber-400 mb-2 font-medium">👀 코드 리뷰 이슈 ({reviewIssues.length})</h3>
          <ul className="space-y-1">
            {reviewIssues.map((issue, i) => (
              <li key={i} className="text-xs text-gray-300 flex items-start gap-2">
                <span className="text-amber-400">•</span>
                {typeof issue === 'string' ? issue : (issue as {issue?: string}).issue}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Review Suggestions */}
      {reviewSuggestions.length > 0 && (
        <div className="bg-blue-900/20 rounded-lg p-3 border border-blue-800/50">
          <h3 className="text-xs text-blue-400 mb-2 font-medium">💡 개선 제안</h3>
          <ul className="space-y-1">
            {reviewSuggestions.map((sug, i) => (
              <li key={i} className="text-xs text-gray-300 flex items-start gap-2">
                <span className="text-blue-400">•</span>
                {typeof sug === 'string' ? sug : (sug as {suggestion?: string}).suggestion}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Code Editor */}
      {content.code && (
        <div className="rounded-lg border border-gray-800 overflow-hidden">
          <div className="px-3 py-1.5 bg-gray-800 flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400">{content.filename || 'code'}</span>
            <span className="text-[10px] text-gray-600">{content.language}</span>
          </div>
          {isEditing ? (
            <textarea
              value={editedContent}
              onChange={(e) => onEditedContentChange(e.target.value)}
              className="w-full p-3 font-mono text-xs bg-gray-950 text-gray-300 focus:outline-none resize-none min-h-[250px]"
            />
          ) : (
            <SyntaxHighlighter
              language={content.language || 'python'}
              style={oneDark}
              customStyle={{ margin: 0, borderRadius: 0, fontSize: '12px' }}
            >
              {content.code}
            </SyntaxHighlighter>
          )}
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
    <div className="space-y-3">
      {content.summary && (
        <div className="text-sm text-gray-400 mb-2">{content.summary}</div>
      )}
      <div className="rounded-lg border border-gray-800 overflow-hidden">
        <div className="px-3 py-1.5 bg-gray-800 flex items-center justify-between">
          <span className="text-xs font-mono text-gray-400">{content.filename || 'Edit'}</span>
          <span className="text-[10px] text-amber-500">editing</span>
        </div>
        <textarea
          value={editedContent}
          onChange={(e) => onEditedContentChange(e.target.value)}
          className="w-full p-3 font-mono text-xs bg-gray-950 text-gray-300 focus:outline-none resize-none min-h-[300px]"
        />
      </div>
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
    <div className="space-y-3">
      {content.summary && (
        <div className="text-sm text-gray-400 mb-2">{content.summary}</div>
      )}
      <div className="grid gap-2 md:grid-cols-2">
        {content.options?.map((opt) => (
          <button
            key={opt.option_id}
            onClick={() => onOptionSelect(opt.option_id)}
            className={`text-left p-3 rounded-lg border transition-all ${
              selectedOption === opt.option_id
                ? 'border-green-500 bg-green-900/20'
                : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <h4 className="text-sm font-medium text-gray-200">{opt.title}</h4>
              {opt.recommended && (
                <span className="text-[10px] px-1.5 py-0.5 bg-green-600 text-white rounded">rec</span>
              )}
            </div>
            <p className="text-xs text-gray-500 mb-2">{opt.description}</p>
            {opt.pros.length > 0 && (
              <div className="text-[10px] text-green-400">+ {opt.pros.join(', ')}</div>
            )}
            {opt.cons.length > 0 && (
              <div className="text-[10px] text-red-400">- {opt.cons.join(', ')}</div>
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
    <div className="space-y-3">
      <div className="bg-red-900/30 rounded-lg p-3 border border-red-800">
        <div className="flex items-center gap-2">
          <AlertIcon className="text-red-400" />
          <p className="text-sm text-red-300">
            {content.action_description || 'This action requires confirmation.'}
          </p>
        </div>
      </div>
      {content.risks && content.risks.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
          <h3 className="text-xs text-gray-500 mb-2">Risks</h3>
          <ul className="space-y-1">
            {content.risks.map((r, i) => (
              <li key={i} className="text-xs text-red-400 flex items-start gap-1">
                <span>•</span> {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

const WorkflowPlanPreview = ({ plan }: { plan: Record<string, unknown> }) => {
  const stages = (plan.stages as Array<{name: string; agents?: string[]; hitl_required?: boolean}>) || [];
  return (
    <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
      <h3 className="text-xs text-gray-500 mb-2">Workflow Plan</h3>
      <div className="space-y-1">
        {stages.map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px]">{i + 1}</span>
            <span className="text-gray-300">{s.name}</span>
            {s.hitl_required && <span className="text-[10px] px-1 py-0.5 bg-amber-600 text-white rounded">HITL</span>}
          </div>
        ))}
      </div>
    </div>
  );
};

// Icons
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

const EditIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
  </svg>
);

const RetryIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
  </svg>
);

const AlertIcon = ({ className = '' }: { className?: string }) => (
  <svg className={`w-4 h-4 ${className}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
  </svg>
);

const getCheckpointStyles = (type: string) => {
  switch (type) {
    case 'approval': return 'bg-green-600 text-white';
    case 'review': return 'bg-blue-600 text-white';
    case 'edit': return 'bg-amber-600 text-white';
    case 'choice': return 'bg-purple-600 text-white';
    case 'confirm': return 'bg-red-600 text-white';
    default: return 'bg-gray-600 text-white';
  }
};

const getCheckpointIcon = (type: string) => {
  switch (type) {
    case 'approval': return <CheckIcon />;
    case 'review': return <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>;
    case 'edit': return <EditIcon />;
    case 'choice': return <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M8.25 15L12 18.75 15.75 15m-7.5-6L12 5.25 15.75 9" /></svg>;
    case 'confirm': return <AlertIcon />;
    default: return <CheckIcon />;
  }
};

export default HITLModal;
