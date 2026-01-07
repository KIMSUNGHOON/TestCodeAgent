/**
 * FileTreeViewer - 파일 트리 구조 및 코드 뷰어 팝업
 * 생성된 파일들을 트리 구조로 표시하고 클릭 시 코드 뷰어 팝업 표시
 */
import { useState, useMemo } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Artifact } from '../types/api';

interface FileTreeViewerProps {
  files: Artifact[];
  onDownloadZip?: () => void;
  isDownloading?: boolean;
}

interface TreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: TreeNode[];
  artifact?: Artifact;
}

// 파일 확장자별 아이콘
const getFileIcon = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const iconMap: Record<string, string> = {
    // Programming languages
    py: '🐍',
    js: '📜',
    ts: '💠',
    tsx: '⚛️',
    jsx: '⚛️',
    java: '☕',
    c: '🔧',
    cpp: '🔧',
    h: '📋',
    cs: '🔷',
    go: '🐹',
    rs: '🦀',
    rb: '💎',
    php: '🐘',
    swift: '🐦',
    kt: '🟣',
    scala: '🔴',
    // Web
    html: '🌐',
    css: '🎨',
    scss: '🎨',
    sass: '🎨',
    less: '🎨',
    vue: '💚',
    svelte: '🧡',
    // Data
    json: '📋',
    xml: '📄',
    yaml: '📄',
    yml: '📄',
    toml: '📄',
    csv: '📊',
    sql: '🗃️',
    // Docs
    md: '📝',
    txt: '📄',
    rst: '📄',
    // Config
    env: '⚙️',
    gitignore: '🙈',
    dockerfile: '🐳',
    // Default
    '': '📄',
  };
  return iconMap[ext] || '📄';
};

// 파일 목록을 트리 구조로 변환
const buildFileTree = (files: Artifact[]): TreeNode[] => {
  const root: TreeNode[] = [];

  files.forEach(file => {
    const parts = file.filename.replace(/\\/g, '/').split('/').filter(Boolean);
    let currentLevel = root;
    let currentPath = '';

    parts.forEach((part, index) => {
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isFile = index === parts.length - 1;

      let existing = currentLevel.find(node => node.name === part);

      if (!existing) {
        const newNode: TreeNode = {
          name: part,
          path: currentPath,
          type: isFile ? 'file' : 'folder',
          children: isFile ? undefined : [],
          artifact: isFile ? file : undefined,
        };
        currentLevel.push(newNode);
        existing = newNode;
      }

      if (!isFile && existing.children) {
        currentLevel = existing.children;
      }
    });
  });

  // 정렬: 폴더 먼저, 그 다음 파일 (알파벳 순)
  const sortNodes = (nodes: TreeNode[]): TreeNode[] => {
    return nodes.sort((a, b) => {
      if (a.type !== b.type) {
        return a.type === 'folder' ? -1 : 1;
      }
      return a.name.localeCompare(b.name);
    }).map(node => ({
      ...node,
      children: node.children ? sortNodes(node.children) : undefined,
    }));
  };

  return sortNodes(root);
};

// 트리 노드 컴포넌트
const TreeNodeComponent = ({
  node,
  depth = 0,
  onFileClick,
  expandedFolders,
  toggleFolder,
}: {
  node: TreeNode;
  depth?: number;
  onFileClick: (artifact: Artifact) => void;
  expandedFolders: Set<string>;
  toggleFolder: (path: string) => void;
}) => {
  const isExpanded = expandedFolders.has(node.path);

  return (
    <div>
      <div
        className={`flex items-center gap-1.5 py-0.5 px-1 rounded cursor-pointer hover:bg-gray-700/50 transition-colors ${
          node.type === 'file' ? 'ml-4' : ''
        }`}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
        onClick={() => {
          if (node.type === 'folder') {
            toggleFolder(node.path);
          } else if (node.artifact) {
            onFileClick(node.artifact);
          }
        }}
      >
        {node.type === 'folder' && (
          <span className="text-gray-500 text-[10px] w-3">
            {isExpanded ? '▼' : '▶'}
          </span>
        )}
        <span className="text-sm">
          {node.type === 'folder' ? (isExpanded ? '📂' : '📁') : getFileIcon(node.name)}
        </span>
        <span className={`text-xs truncate ${
          node.type === 'folder' ? 'text-yellow-400 font-medium' : 'text-gray-300'
        }`}>
          {node.name}
        </span>
        {node.artifact?.action && (
          <span className={`text-[9px] px-1 rounded ${
            node.artifact.action === 'created'
              ? 'bg-green-500/20 text-green-400'
              : node.artifact.action === 'modified'
              ? 'bg-yellow-500/20 text-yellow-400'
              : 'bg-gray-500/20 text-gray-400'
          }`}>
            {node.artifact.action === 'created' ? 'NEW' :
             node.artifact.action === 'modified' ? 'MOD' : ''}
          </span>
        )}
      </div>
      {node.type === 'folder' && isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNodeComponent
              key={child.path}
              node={child}
              depth={depth + 1}
              onFileClick={onFileClick}
              expandedFolders={expandedFolders}
              toggleFolder={toggleFolder}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// 코드 뷰어 모달
const CodeViewerModal = ({
  artifact,
  onClose
}: {
  artifact: Artifact;
  onClose: () => void;
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50 rounded-t-xl">
          <div className="flex items-center gap-3">
            <span className="text-lg">{getFileIcon(artifact.filename)}</span>
            <div>
              <h3 className="text-sm font-medium text-gray-200">{artifact.filename}</h3>
              <div className="flex items-center gap-2 text-[10px] text-gray-500">
                <span className="px-1.5 py-0.5 bg-gray-700 rounded">{artifact.language}</span>
                {artifact.saved_path && (
                  <span className="truncate max-w-[300px]" title={artifact.saved_path}>
                    {artifact.saved_path}
                  </span>
                )}
                {artifact.action && (
                  <span className={`px-1.5 py-0.5 rounded ${
                    artifact.action === 'created'
                      ? 'bg-green-500/20 text-green-400'
                      : artifact.action === 'modified'
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-gray-500/20 text-gray-400'
                  }`}>
                    {artifact.action === 'created' ? '생성됨' :
                     artifact.action === 'modified' ? '수정됨' : artifact.action}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors"
            >
              {copied ? '✓ 복사됨' : '📋 복사'}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* 코드 내용 */}
        <div className="flex-1 overflow-auto">
          <SyntaxHighlighter
            style={oneDark}
            language={artifact.language || 'text'}
            showLineNumbers
            customStyle={{
              margin: 0,
              borderRadius: 0,
              fontSize: '12px',
              background: 'transparent',
            }}
            lineNumberStyle={{
              minWidth: '3em',
              paddingRight: '1em',
              color: '#6b7280',
              borderRight: '1px solid #374151',
              marginRight: '1em',
            }}
          >
            {artifact.content}
          </SyntaxHighlighter>
        </div>

        {/* 푸터 */}
        <div className="px-4 py-2 border-t border-gray-700 bg-gray-800/30 rounded-b-xl">
          <div className="flex items-center justify-between text-[10px] text-gray-500">
            <span>{artifact.content.split('\n').length} 줄</span>
            <span>{artifact.content.length.toLocaleString()} 문자</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// 메인 컴포넌트
const FileTreeViewer = ({ files, onDownloadZip, isDownloading }: FileTreeViewerProps) => {
  const [selectedFile, setSelectedFile] = useState<Artifact | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<'tree' | 'list'>('tree');

  const fileTree = useMemo(() => buildFileTree(files), [files]);

  // 모든 폴더 펼치기
  const expandAll = () => {
    const allFolders = new Set<string>();
    const collectFolders = (nodes: TreeNode[]) => {
      nodes.forEach(node => {
        if (node.type === 'folder') {
          allFolders.add(node.path);
          if (node.children) collectFolders(node.children);
        }
      });
    };
    collectFolders(fileTree);
    setExpandedFolders(allFolders);
  };

  // 모든 폴더 접기
  const collapseAll = () => {
    setExpandedFolders(new Set());
  };

  // 폴더 토글
  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  // 통계
  const stats = useMemo(() => {
    const created = files.filter(f => f.action === 'created').length;
    const modified = files.filter(f => f.action === 'modified').length;
    const folders = new Set(files.map(f => {
      const parts = f.filename.replace(/\\/g, '/').split('/');
      return parts.slice(0, -1).join('/');
    }).filter(Boolean)).size;
    return { total: files.length, created, modified, folders };
  }, [files]);

  if (files.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-lg overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800 bg-gray-800/50">
        <div className="flex items-center gap-2">
          <span className="text-green-400">📁</span>
          <span className="text-xs font-medium text-gray-300">생성된 파일</span>
          <span className="px-1.5 py-0.5 bg-gray-700 rounded text-[10px] text-gray-400">
            {stats.total}개
          </span>
          {stats.created > 0 && (
            <span className="px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded text-[10px]">
              +{stats.created} 생성
            </span>
          )}
          {stats.modified > 0 && (
            <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-[10px]">
              {stats.modified} 수정
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {/* 뷰 모드 토글 */}
          <button
            onClick={() => setViewMode(viewMode === 'tree' ? 'list' : 'tree')}
            className="p-1 text-gray-500 hover:text-gray-300 hover:bg-gray-700 rounded transition-colors"
            title={viewMode === 'tree' ? '목록 보기' : '트리 보기'}
          >
            {viewMode === 'tree' ? '☰' : '🌲'}
          </button>

          {viewMode === 'tree' && (
            <>
              <button
                onClick={expandAll}
                className="p-1 text-gray-500 hover:text-gray-300 hover:bg-gray-700 rounded transition-colors text-[10px]"
                title="모두 펼치기"
              >
                ⊞
              </button>
              <button
                onClick={collapseAll}
                className="p-1 text-gray-500 hover:text-gray-300 hover:bg-gray-700 rounded transition-colors text-[10px]"
                title="모두 접기"
              >
                ⊟
              </button>
            </>
          )}

          {/* ZIP 다운로드 */}
          {onDownloadZip && (
            <button
              onClick={onDownloadZip}
              disabled={isDownloading}
              className="flex items-center gap-1 px-2 py-1 text-[10px] bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 text-white rounded transition-colors ml-2"
              title="ZIP으로 다운로드"
            >
              {isDownloading ? (
                <>
                  <span className="animate-spin">⟳</span>
                  <span>압축 중...</span>
                </>
              ) : (
                <>
                  <span>📦</span>
                  <span>ZIP 다운로드</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* 파일 목록 */}
      <div className="max-h-64 overflow-y-auto p-2">
        {viewMode === 'tree' ? (
          <div className="space-y-0.5">
            {fileTree.map(node => (
              <TreeNodeComponent
                key={node.path}
                node={node}
                onFileClick={setSelectedFile}
                expandedFolders={expandedFolders}
                toggleFolder={toggleFolder}
              />
            ))}
          </div>
        ) : (
          <div className="space-y-0.5">
            {files.map((file, i) => (
              <div
                key={`${file.filename}-${i}`}
                className="flex items-center gap-2 py-1 px-2 rounded cursor-pointer hover:bg-gray-700/50 transition-colors"
                onClick={() => setSelectedFile(file)}
              >
                <span>{getFileIcon(file.filename)}</span>
                <span className="text-xs text-gray-300 truncate flex-1">{file.filename}</span>
                <span className="text-[9px] text-gray-600">[{file.language}]</span>
                {file.action && (
                  <span className={`text-[9px] px-1 rounded ${
                    file.action === 'created'
                      ? 'bg-green-500/20 text-green-400'
                      : file.action === 'modified'
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-gray-500/20 text-gray-400'
                  }`}>
                    {file.action === 'created' ? 'NEW' :
                     file.action === 'modified' ? 'MOD' : ''}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 코드 뷰어 모달 */}
      {selectedFile && (
        <CodeViewerModal
          artifact={selectedFile}
          onClose={() => setSelectedFile(null)}
        />
      )}
    </div>
  );
};

export default FileTreeViewer;
