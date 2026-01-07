/**
 * Workspace utility functions for cross-platform support
 */

/**
 * Detect if running on Windows based on navigator.platform
 * Note: This is for UI hints only; actual workspace paths should come from backend
 */
export function isWindows(): boolean {
  if (typeof window === 'undefined') return false;
  return navigator.platform.toLowerCase().includes('win');
}

/**
 * Get default workspace path placeholder based on detected OS
 * For actual workspace operations, use the backend-provided path
 */
export function getDefaultWorkspacePlaceholder(): string {
  if (isWindows()) {
    return 'C:\\Users\\username\\workspace';
  }
  return '/home/user/workspace';
}

/**
 * Get default workspace path - tries localStorage first, then falls back to placeholder
 */
export function getDefaultWorkspace(): string {
  const stored = localStorage.getItem('workflow_workspace');
  if (stored) return stored;
  return getDefaultWorkspacePlaceholder();
}

/**
 * Normalize path separators for display
 * Converts backslashes to forward slashes for consistent display
 */
export function normalizePathForDisplay(path: string): string {
  return path.replace(/\\/g, '/');
}

/**
 * Get basename from path (works with both / and \ separators)
 */
export function getBasename(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}
