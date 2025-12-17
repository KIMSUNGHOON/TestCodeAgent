/**
 * Terminal component - Simple shell interface for workspace
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import apiClient from '../api/client';

interface CommandEntry {
  command: string;
  stdout: string;
  stderr: string;
  returnCode: number;
  cwd: string;
  timestamp: number;
}

interface TerminalProps {
  sessionId: string;
  workspace: string;
  isVisible: boolean;
  onClose: () => void;
}

const Terminal = ({ sessionId, workspace, isVisible, onClose }: TerminalProps) => {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<CommandEntry[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [history]);

  // Focus input when visible
  useEffect(() => {
    if (isVisible && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isVisible]);

  const executeCommand = useCallback(async (command: string) => {
    if (!command.trim()) return;

    setIsExecuting(true);

    try {
      const result = await apiClient.executeShellCommand(sessionId, command);

      setHistory(prev => [...prev, {
        command,
        stdout: result.stdout || '',
        stderr: result.stderr || result.error || '',
        returnCode: result.return_code ?? (result.success ? 0 : 1),
        cwd: result.cwd || workspace,
        timestamp: Date.now()
      }]);
    } catch (err) {
      setHistory(prev => [...prev, {
        command,
        stdout: '',
        stderr: err instanceof Error ? err.message : 'Unknown error',
        returnCode: 1,
        cwd: workspace,
        timestamp: Date.now()
      }]);
    } finally {
      setIsExecuting(false);
      setInput('');
      setHistoryIndex(-1);
    }
  }, [sessionId, workspace]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeCommand(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length > 0 && historyIndex < history.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setInput(history[history.length - 1 - newIndex].command);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInput(history[history.length - 1 - newIndex].command);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInput('');
      }
    }
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-[#1E1E1E] rounded-lg shadow-2xl w-[900px] h-[600px] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 bg-[#323232] border-b border-[#3C3C3C]">
          <div className="flex items-center gap-3">
            <div className="flex gap-2">
              <button
                onClick={onClose}
                className="w-3 h-3 rounded-full bg-[#FF5F57] hover:bg-[#FF3B30] transition-colors"
              />
              <div className="w-3 h-3 rounded-full bg-[#FEBC2E]" />
              <div className="w-3 h-3 rounded-full bg-[#28C840]" />
            </div>
            <div className="flex items-center gap-2 text-white text-sm">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
              </svg>
              <span>Terminal</span>
              <span className="text-[#888888]">- {workspace}</span>
            </div>
          </div>
          <button
            onClick={() => setHistory([])}
            className="text-[#888888] hover:text-white text-xs transition-colors"
          >
            Clear
          </button>
        </div>

        {/* Output Area */}
        <div
          ref={outputRef}
          className="flex-1 overflow-y-auto p-4 font-mono text-sm"
        >
          {/* Welcome message */}
          {history.length === 0 && (
            <div className="text-[#888888] mb-4">
              <p>Welcome to the workspace terminal.</p>
              <p>Current directory: {workspace}</p>
              <p className="text-[#666666] mt-2">Type commands to execute in your workspace.</p>
            </div>
          )}

          {/* Command history */}
          {history.map((entry, idx) => (
            <div key={idx} className="mb-4">
              {/* Command prompt */}
              <div className="flex items-start gap-2">
                <span className="text-[#16A34A] flex-shrink-0">
                  {entry.cwd.split('/').pop() || '~'}$
                </span>
                <span className="text-white">{entry.command}</span>
              </div>

              {/* Output */}
              {entry.stdout && (
                <pre className="text-[#D4D4D4] whitespace-pre-wrap mt-1 ml-4">
                  {entry.stdout}
                </pre>
              )}

              {/* Errors */}
              {entry.stderr && (
                <pre className="text-[#F87171] whitespace-pre-wrap mt-1 ml-4">
                  {entry.stderr}
                </pre>
              )}

              {/* Return code indicator for non-zero */}
              {entry.returnCode !== 0 && (
                <div className="text-[#888888] text-xs mt-1 ml-4">
                  Exit code: {entry.returnCode}
                </div>
              )}
            </div>
          ))}

          {/* Executing indicator */}
          {isExecuting && (
            <div className="flex items-center gap-2 text-[#888888]">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span>Executing...</span>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-[#3C3C3C] p-4">
          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <span className="text-[#16A34A] font-mono text-sm flex-shrink-0">
              {workspace.split('/').pop() || '~'}$
            </span>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isExecuting}
              placeholder="Enter command..."
              className="flex-1 bg-transparent text-white font-mono text-sm focus:outline-none placeholder-[#666666] disabled:opacity-50"
              autoComplete="off"
              spellCheck={false}
            />
            <button
              type="submit"
              disabled={isExecuting || !input.trim()}
              className="px-3 py-1 rounded bg-[#16A34A] hover:bg-[#15803D] disabled:bg-[#3C3C3C] disabled:cursor-not-allowed text-white text-sm transition-colors"
            >
              Run
            </button>
          </form>
          <div className="mt-2 flex items-center gap-4 text-xs text-[#666666]">
            <span>↑↓ Navigate history</span>
            <span>Enter to execute</span>
            <span>Esc to close</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Terminal;
