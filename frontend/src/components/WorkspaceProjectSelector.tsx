/**
 * Unified Workspace and Project Selector
 * Compact dropdown UI for selecting workspace and project
 */
import { useState, useEffect } from 'react';
import apiClient from '../api/client';

interface Project {
  name: string;
  path: string;
  modified: string;
  file_count: number;
}

interface WorkspaceProjectSelectorProps {
  currentWorkspace: string;
  currentProject?: string;
  onWorkspaceChange: (workspace: string) => void;
  onProjectSelect: (projectPath: string) => void;
}

const WorkspaceProjectSelector = ({
  currentWorkspace,
  currentProject,
  onWorkspaceChange,
  onProjectSelect
}: WorkspaceProjectSelectorProps) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [workspaceInput, setWorkspaceInput] = useState(currentWorkspace);
  const [isEditingWorkspace, setIsEditingWorkspace] = useState(false);

  // Load projects when dropdown opens
  useEffect(() => {
    if (showDropdown) {
      loadProjects();
    }
  }, [showDropdown, currentWorkspace]);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const response = await apiClient.listProjects(currentWorkspace);
      if (response.success && response.projects) {
        setProjects(response.projects);
      }
    } catch (err) {
      console.error('Error loading projects:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleWorkspaceSave = () => {
    if (workspaceInput && workspaceInput !== currentWorkspace) {
      onWorkspaceChange(workspaceInput);
    }
    setIsEditingWorkspace(false);
  };

  const handleProjectClick = (projectPath: string) => {
    onProjectSelect(projectPath);
    setShowDropdown(false);
  };

  // Extract project name from current workspace
  const displayProjectName = currentProject
    ? currentProject.split('/').pop()
    : currentWorkspace.split('/').pop() || 'workspace';

  return (
    <div className="relative">
      {/* Main Toggle Button */}
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-[#E5E5E5] hover:border-[#DA7756] transition-colors text-sm"
        title="Select Workspace/Project"
      >
        <svg className="w-4 h-4 text-[#666666]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
        </svg>
        <span className="font-medium text-[#1A1A1A] max-w-[150px] truncate">
          {displayProjectName}
        </span>
        <svg className={`w-4 h-4 text-[#666666] transition-transform ${showDropdown ? '' : 'rotate-180'}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {/* Dropdown */}
      {showDropdown && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setShowDropdown(false)} />

          {/* Dropdown Content */}
          <div className="absolute bottom-full left-0 mb-2 w-80 bg-white rounded-lg shadow-lg border border-[#E5E5E5] z-50 max-h-96 overflow-hidden flex flex-col">
            {/* Workspace Section */}
            <div className="p-3 border-b border-[#E5E5E5] bg-[#F9F9F9]">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-[#666666] uppercase">Workspace</span>
                {!isEditingWorkspace ? (
                  <button
                    onClick={() => setIsEditingWorkspace(true)}
                    className="text-xs text-[#DA7756] hover:text-[#C66646] font-medium"
                  >
                    Change
                  </button>
                ) : (
                  <button
                    onClick={handleWorkspaceSave}
                    className="text-xs text-green-600 hover:text-green-700 font-medium"
                  >
                    Save
                  </button>
                )}
              </div>
              {isEditingWorkspace ? (
                <input
                  type="text"
                  value={workspaceInput}
                  onChange={(e) => setWorkspaceInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleWorkspaceSave();
                    if (e.key === 'Escape') setIsEditingWorkspace(false);
                  }}
                  className="w-full px-2 py-1 text-sm border border-[#DA7756] rounded focus:outline-none focus:ring-2 focus:ring-[#DA7756]"
                  placeholder="/home/user/workspace"
                  autoFocus
                />
              ) : (
                <div className="text-sm text-[#1A1A1A] font-mono bg-white px-2 py-1 rounded border border-[#E5E5E5] truncate">
                  {currentWorkspace}
                </div>
              )}
            </div>

            {/* Projects Section */}
            <div className="flex-1 overflow-y-auto">
              <div className="p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#666666] uppercase">Projects</span>
                  <button
                    onClick={loadProjects}
                    disabled={loading}
                    className="text-xs text-[#DA7756] hover:text-[#C66646] font-medium disabled:opacity-50"
                  >
                    {loading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>

                {loading ? (
                  <div className="text-center py-8 text-[#999999] text-sm">
                    Loading projects...
                  </div>
                ) : projects.length === 0 ? (
                  <div className="text-center py-8 text-[#999999] text-sm">
                    No projects found
                    <br />
                    <span className="text-xs">Start a new conversation to create a project</span>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {projects.map((project) => {
                      const isActive = currentProject === project.path || currentWorkspace === project.path;
                      return (
                        <button
                          key={project.path}
                          onClick={() => handleProjectClick(project.path)}
                          className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                            isActive
                              ? 'bg-[#DA775610] border border-[#DA7756]'
                              : 'hover:bg-[#F5F5F5] border border-transparent'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <svg className="w-4 h-4 text-[#DA7756] flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
                                </svg>
                                <span className="font-medium text-[#1A1A1A] text-sm truncate">
                                  {project.name}
                                </span>
                              </div>
                              <div className="mt-1 flex items-center gap-3 text-xs text-[#999999]">
                                <span>{project.file_count} files</span>
                                <span>{new Date(project.modified).toLocaleDateString()}</span>
                              </div>
                            </div>
                            {isActive && (
                              <svg className="w-5 h-5 text-[#DA7756] flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                              </svg>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default WorkspaceProjectSelector;
