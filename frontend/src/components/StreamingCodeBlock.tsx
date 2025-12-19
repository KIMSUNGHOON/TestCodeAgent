/**
 * StreamingCodeBlock - Real-time code generation display
 * Shows code being generated token by token with syntax highlighting
 */
import React, { useEffect, useRef } from 'react';

interface StreamingCodeBlockProps {
  filename: string;
  language: string;
  content: string;
  isStreaming: boolean;
  agent?: string;
  agentTitle?: string;
}

// Simple syntax highlighting (can be enhanced with prism/highlight.js)
const highlightCode = (code: string, language: string): string => {
  // Basic keyword highlighting for Python
  if (language === 'python' || language === 'py') {
    return code
      .replace(/\b(def|class|import|from|return|if|else|elif|for|while|try|except|finally|with|as|async|await|yield|lambda|pass|break|continue|raise|True|False|None|and|or|not|in|is)\b/g, '<span class="text-purple-600 font-medium">$1</span>')
      .replace(/\b(self|cls)\b/g, '<span class="text-pink-600">$1</span>')
      .replace(/(["'])(.*?)\1/g, '<span class="text-green-600">$&</span>')
      .replace(/(#.*$)/gm, '<span class="text-gray-500 italic">$1</span>')
      .replace(/\b(\d+)\b/g, '<span class="text-orange-500">$1</span>');
  }

  // TypeScript/JavaScript
  if (['typescript', 'javascript', 'ts', 'js', 'tsx', 'jsx'].includes(language)) {
    return code
      .replace(/\b(const|let|var|function|return|if|else|for|while|try|catch|finally|async|await|export|import|from|class|extends|interface|type|enum|new|this|super|static|public|private|protected)\b/g, '<span class="text-purple-600 font-medium">$1</span>')
      .replace(/(["'`])(.*?)\1/g, '<span class="text-green-600">$&</span>')
      .replace(/(\/\/.*$)/gm, '<span class="text-gray-500 italic">$1</span>')
      .replace(/\b(\d+)\b/g, '<span class="text-orange-500">$1</span>');
  }

  return code;
};

export const StreamingCodeBlock: React.FC<StreamingCodeBlockProps> = ({
  filename,
  language,
  content,
  isStreaming,
  agent,
  agentTitle,
}) => {
  const codeRef = useRef<HTMLPreElement>(null);

  // Auto-scroll to bottom when streaming
  useEffect(() => {
    if (codeRef.current && isStreaming) {
      codeRef.current.scrollTop = codeRef.current.scrollHeight;
    }
  }, [content, isStreaming]);

  const lines = content.split('\n');
  const highlightedCode = highlightCode(content, language);

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-3">
          {/* File icon */}
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <span className="text-sm font-mono text-gray-300">{filename}</span>
          </div>

          {/* Language badge */}
          <span className="px-2 py-0.5 text-xs font-medium bg-gray-700 text-gray-300 rounded">
            {language}
          </span>

          {/* Streaming indicator */}
          {isStreaming && (
            <div className="flex items-center gap-2 text-green-400">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              <span className="text-xs">Generating...</span>
            </div>
          )}
        </div>

        {/* Agent info */}
        {agentTitle && (
          <span className="text-xs text-gray-400">
            by {agentTitle}
          </span>
        )}
      </div>

      {/* Code content */}
      <pre
        ref={codeRef}
        className="p-4 overflow-auto max-h-96 text-sm font-mono text-gray-300 leading-relaxed"
      >
        <code dangerouslySetInnerHTML={{ __html: highlightedCode }} />
        {isStreaming && (
          <span className="inline-block w-2 h-4 bg-green-400 animate-pulse ml-0.5" />
        )}
      </pre>

      {/* Footer */}
      <div className="px-4 py-2 bg-gray-800 border-t border-gray-700 flex items-center justify-between text-xs text-gray-500">
        <span>{lines.length} lines</span>
        <span>{content.length} characters</span>
      </div>
    </div>
  );
};

export default StreamingCodeBlock;
