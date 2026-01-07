/**
 * PromptViewer component - Collapsible viewer for input/output prompts
 */
import { useState } from 'react';
import { PromptInfo } from '../types/api';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface PromptViewerProps {
  promptInfo: PromptInfo;
  agentName?: string;
}

type TabType = 'system' | 'user' | 'output';

const PromptViewer = ({ promptInfo, agentName: _agentName }: PromptViewerProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('system');

  const tabs: { id: TabType; label: string; content: string | undefined }[] = [
    { id: 'system', label: 'System Prompt', content: promptInfo.system_prompt },
    { id: 'user', label: 'User Input', content: promptInfo.user_prompt },
    { id: 'output', label: 'Output', content: promptInfo.output },
  ];

  return (
    <div className="mt-3 rounded-xl border border-[#E5E5E5] bg-[#FAFAFA] overflow-hidden">
      {/* Header with toggle */}
      <div
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-[#F5F4F2] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <svg
            className={`w-4 h-4 text-[#666666] transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-[#7C3AED]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
            </svg>
            <span className="text-sm font-medium text-[#1A1A1A]">Prompt Details</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {promptInfo.model && (
            <span className="text-xs text-[#666666] bg-white px-2 py-0.5 rounded border border-[#E5E5E5]">
              {promptInfo.model}
            </span>
          )}
          {promptInfo.latency_ms && (
            <span className="text-xs text-[#666666]">
              {promptInfo.latency_ms}ms
            </span>
          )}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-[#E5E5E5]">
          {/* Tab headers */}
          <div className="flex border-b border-[#E5E5E5] bg-white">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveTab(tab.id);
                }}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-[#DA7756] border-b-2 border-[#DA7756] -mb-[1px]'
                    : 'text-[#666666] hover:text-[#1A1A1A]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="max-h-[400px] overflow-auto">
            {tabs.find(t => t.id === activeTab)?.content ? (
              <SyntaxHighlighter
                style={oneDark}
                language="text"
                customStyle={{ margin: 0, borderRadius: 0, fontSize: '12px' }}
                wrapLongLines
              >
                {tabs.find(t => t.id === activeTab)?.content || ''}
              </SyntaxHighlighter>
            ) : (
              <div className="p-4 text-sm text-[#999999] italic">
                No content available
              </div>
            )}
          </div>

          {/* Copy button */}
          <div className="flex justify-end p-2 border-t border-[#E5E5E5] bg-white">
            <button
              onClick={(e) => {
                e.stopPropagation();
                const content = tabs.find(t => t.id === activeTab)?.content;
                if (content) navigator.clipboard.writeText(content);
              }}
              className="text-xs text-[#666666] hover:text-[#1A1A1A] px-3 py-1 rounded hover:bg-[#F5F4F2] flex items-center gap-1"
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
              </svg>
              Copy
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PromptViewer;
