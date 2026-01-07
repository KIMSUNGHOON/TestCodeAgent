/**
 * WorkspaceSettings component - Configure workspace directory for file operations
 */
import { useState, useEffect } from 'react';
import apiClient from '../api/client';

interface WorkspaceSettingsProps {
  workspace: string;
  onWorkspaceChange: (path: string) => void;
  onClose: () => void;
}

interface DirectoryInfo {
  path: string;
  name: string;
  is_directory: boolean;
}

const WorkspaceSettings = ({ workspace, onWorkspaceChange, onClose }: WorkspaceSettingsProps) => {
  const [inputPath, setInputPath] = useState(workspace);
  const [directoryContents, setDirectoryContents] = useState<DirectoryInfo[]>([]);
  const [currentBrowsePath, setCurrentBrowsePath] = useState(workspace || '/home');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showBrowser, setShowBrowser] = useState(false);

  // Load directory contents when browsing
  useEffect(() => {
    if (showBrowser && currentBrowsePath) {
      loadDirectoryContents(currentBrowsePath);
    }
  }, [showBrowser, currentBrowsePath]);

  const loadDirectoryContents = async (path: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.listDirectory(path);
      if (result.success) {
        // Sort: directories first, then files
        const sorted = (result.contents || []).sort((a: DirectoryInfo, b: DirectoryInfo) => {
          if (a.is_directory && !b.is_directory) return -1;
          if (!a.is_directory && b.is_directory) return 1;
          return a.name.localeCompare(b.name);
        });
        setDirectoryContents(sorted);
      } else {
        setError(result.error || 'Failed to load directory');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load directory');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNavigateUp = () => {
    const parentPath = currentBrowsePath.split('/').slice(0, -1).join('/') || '/';
    setCurrentBrowsePath(parentPath);
  };

  const handleSelectDirectory = (dir: DirectoryInfo) => {
    if (dir.is_directory) {
      setCurrentBrowsePath(dir.path);
    }
  };

  const handleConfirmPath = () => {
    if (showBrowser) {
      setInputPath(currentBrowsePath);
      onWorkspaceChange(currentBrowsePath);
    } else {
      onWorkspaceChange(inputPath);
    }
    onClose();
  };

  const handleSelectCurrentBrowsePath = () => {
    setInputPath(currentBrowsePath);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E5E5E5] flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[#1A1A1A]">Workspace Settings</h2>
          <button
            onClick={onClose}
            className="p-2 text-[#666666] hover:text-[#1A1A1A] hover:bg-[#F5F4F2] rounded-lg"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex-1 overflow-y-auto">
          {/* Workspace Path Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-[#1A1A1A] mb-2">
              Workspace Directory
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={inputPath}
                onChange={(e) => setInputPath(e.target.value)}
                placeholder="/path/to/your/project"
                className="flex-1 px-4 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#DA7756] focus:ring-opacity-50"
              />
              <button
                onClick={() => setShowBrowser(!showBrowser)}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                  showBrowser
                    ? 'bg-[#DA7756] text-white'
                    : 'bg-[#F5F4F2] text-[#666666] hover:bg-[#E5E5E5]'
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
                </svg>
                Browse
              </button>
            </div>
            <p className="mt-2 text-xs text-[#999999]">
              Generated code files will be saved to this directory
            </p>
          </div>

          {/* Directory Browser */}
          {showBrowser && (
            <div className="border border-[#E5E5E5] rounded-lg overflow-hidden">
              {/* Current Path */}
              <div className="px-4 py-2 bg-[#F5F4F2] border-b border-[#E5E5E5] flex items-center gap-2">
                <button
                  onClick={handleNavigateUp}
                  disabled={currentBrowsePath === '/'}
                  className="p-1 text-[#666666] hover:text-[#1A1A1A] disabled:opacity-50"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                  </svg>
                </button>
                <span className="text-sm font-mono text-[#666666] flex-1 truncate">
                  {currentBrowsePath}
                </span>
                <button
                  onClick={handleSelectCurrentBrowsePath}
                  className="px-3 py-1 text-xs bg-[#DA7756] text-white rounded hover:bg-[#C86A4A]"
                >
                  Select This
                </button>
              </div>

              {/* Directory Contents */}
              <div className="max-h-60 overflow-y-auto">
                {isLoading ? (
                  <div className="p-4 text-center text-[#999999]">Loading...</div>
                ) : error ? (
                  <div className="p-4 text-center text-red-500">{error}</div>
                ) : directoryContents.length === 0 ? (
                  <div className="p-4 text-center text-[#999999]">Empty directory</div>
                ) : (
                  <div className="divide-y divide-[#E5E5E5]">
                    {directoryContents.filter(d => d.is_directory).map((item) => (
                      <button
                        key={item.path}
                        onClick={() => handleSelectDirectory(item)}
                        className="w-full px-4 py-2 flex items-center gap-3 hover:bg-[#F5F4F2] text-left"
                      >
                        <svg className="w-5 h-5 text-[#DA7756]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
                        </svg>
                        <span className="text-sm text-[#1A1A1A]">{item.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* File Operations Info */}
          <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
            <h3 className="text-sm font-medium text-blue-700 mb-2">File Operations</h3>
            <ul className="text-xs text-blue-600 space-y-1">
              <li className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Generated code will be automatically saved to workspace
              </li>
              <li className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Existing files can be read for context
              </li>
              <li className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Multi-file projects are fully supported
              </li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#E5E5E5] flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-[#666666] hover:bg-[#F5F4F2] rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirmPath}
            className="px-4 py-2 bg-[#DA7756] text-white rounded-lg hover:bg-[#C86A4A]"
          >
            Save Workspace
          </button>
        </div>
      </div>
    </div>
  );
};

export default WorkspaceSettings;
