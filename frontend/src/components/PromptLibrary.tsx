/**
 * PromptLibrary component - Right sidebar with preset prompts
 */
import { useState } from 'react';

interface Prompt {
  id: string;
  category: string;
  title: string;
  prompt: string;
  icon: string;
}

interface PromptLibraryProps {
  onPromptSelect: (prompt: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

const PROMPT_LIBRARY: Prompt[] = [
  // Coding
  {
    id: 'new-feature',
    category: '💻 Coding',
    title: 'New Feature',
    prompt: 'Create a new feature that [describe functionality]. Include error handling, input validation, and comprehensive documentation.',
    icon: '✨'
  },
  {
    id: 'api-endpoint',
    category: '💻 Coding',
    title: 'API Endpoint',
    prompt: 'Implement a REST API endpoint for [describe purpose]. Include request/response validation, error handling, and proper HTTP status codes.',
    icon: '🔌'
  },
  {
    id: 'component',
    category: '💻 Coding',
    title: 'UI Component',
    prompt: 'Create a [component name] component with [list features]. Make it reusable, accessible, and responsive.',
    icon: '🎨'
  },

  // Refactoring
  {
    id: 'refactor-clean',
    category: '♻️ Refactoring',
    title: 'Clean Code',
    prompt: 'Refactor [file/function name] to improve code quality. Apply SOLID principles, remove code smells, and improve readability.',
    icon: '🧹'
  },
  {
    id: 'extract-function',
    category: '♻️ Refactoring',
    title: 'Extract Functions',
    prompt: 'Extract reusable functions from [file name]. Create pure functions with clear responsibilities and proper naming.',
    icon: '📦'
  },
  {
    id: 'optimize-performance',
    category: '♻️ Refactoring',
    title: 'Optimize Performance',
    prompt: 'Optimize the performance of [file/function name]. Focus on algorithmic efficiency, memory usage, and reducing complexity.',
    icon: '⚡'
  },

  // Debugging
  {
    id: 'fix-bug',
    category: '🐛 Debugging',
    title: 'Fix Bug',
    prompt: 'Fix the bug in [file name] where [describe issue]. Identify the root cause, implement a fix, and add tests to prevent regression.',
    icon: '🔧'
  },
  {
    id: 'add-logging',
    category: '🐛 Debugging',
    title: 'Add Logging',
    prompt: 'Add comprehensive logging to [file/function name]. Include debug, info, warning, and error levels with meaningful context.',
    icon: '📝'
  },
  {
    id: 'error-handling',
    category: '🐛 Debugging',
    title: 'Error Handling',
    prompt: 'Improve error handling in [file name]. Add try-catch blocks, meaningful error messages, and proper error propagation.',
    icon: '⚠️'
  },

  // Testing
  {
    id: 'unit-tests',
    category: '✅ Testing',
    title: 'Unit Tests',
    prompt: 'Write comprehensive unit tests for [file/function name]. Cover edge cases, error scenarios, and achieve >80% code coverage.',
    icon: '🧪'
  },
  {
    id: 'integration-tests',
    category: '✅ Testing',
    title: 'Integration Tests',
    prompt: 'Create integration tests for [feature/module name]. Test component interactions, API calls, and end-to-end workflows.',
    icon: '🔗'
  },
  {
    id: 'test-fixtures',
    category: '✅ Testing',
    title: 'Test Fixtures',
    prompt: 'Create test fixtures and mock data for [feature name]. Include various scenarios: normal, edge cases, and error conditions.',
    icon: '📊'
  },

  // Documentation
  {
    id: 'add-docs',
    category: '📚 Documentation',
    title: 'Add Documentation',
    prompt: 'Write comprehensive documentation for [file/module name]. Include purpose, usage examples, parameters, return values, and edge cases.',
    icon: '📖'
  },
  {
    id: 'api-docs',
    category: '📚 Documentation',
    title: 'API Documentation',
    prompt: 'Generate API documentation for [endpoint/service name]. Include request/response examples, authentication, and error codes.',
    icon: '📜'
  },
  {
    id: 'readme',
    category: '📚 Documentation',
    title: 'README',
    prompt: 'Create a comprehensive README for [project/feature name]. Include setup instructions, usage examples, architecture overview, and contribution guidelines.',
    icon: '📄'
  },

  // Architecture
  {
    id: 'design-pattern',
    category: '🏗️ Architecture',
    title: 'Apply Pattern',
    prompt: 'Refactor [code section] to use the [pattern name] design pattern. Explain the benefits and how it improves the codebase.',
    icon: '🎯'
  },
  {
    id: 'database-schema',
    category: '🏗️ Architecture',
    title: 'Database Schema',
    prompt: 'Design a database schema for [feature description]. Include tables, relationships, indexes, and constraints. Consider normalization and performance.',
    icon: '🗄️'
  },
  {
    id: 'system-design',
    category: '🏗️ Architecture',
    title: 'System Design',
    prompt: 'Design a scalable system architecture for [feature/service description]. Consider components, data flow, APIs, caching, and monitoring.',
    icon: '🏛️'
  }
];

const PromptLibrary = ({ onPromptSelect, isOpen, onClose }: PromptLibraryProps) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState('');

  const categories = ['All', ...Array.from(new Set(PROMPT_LIBRARY.map(p => p.category)))];

  const filteredPrompts = PROMPT_LIBRARY.filter(prompt => {
    const matchesCategory = selectedCategory === 'All' || prompt.category === selectedCategory;
    const matchesSearch = searchQuery === '' ||
      prompt.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      prompt.prompt.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-20 z-40"
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-50 flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E5E5E5]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-[#1A1A1A]">Prompt Library</h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-[#F5F4F2] rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-[#666666]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Search */}
          <div className="relative">
            <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[#999999]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              type="text"
              placeholder="Search prompts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:border-[#DA7756] transition-colors"
            />
          </div>
        </div>

        {/* Categories */}
        <div className="px-6 py-3 border-b border-[#E5E5E5] overflow-x-auto">
          <div className="flex gap-2">
            {categories.map(category => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                  selectedCategory === category
                    ? 'bg-[#DA7756] text-white'
                    : 'bg-[#F5F4F2] text-[#666666] hover:bg-[#E5E5E5]'
                }`}
              >
                {category}
              </button>
            ))}
          </div>
        </div>

        {/* Prompt List */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {filteredPrompts.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#F5F4F2] flex items-center justify-center">
                <svg className="w-8 h-8 text-[#999999]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                </svg>
              </div>
              <p className="text-sm text-[#666666]">No prompts found</p>
              <p className="text-xs text-[#999999] mt-1">Try a different search or category</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredPrompts.map(prompt => (
                <button
                  key={prompt.id}
                  onClick={() => {
                    onPromptSelect(prompt.prompt);
                    onClose();
                  }}
                  className="w-full text-left p-4 rounded-xl border border-[#E5E5E5] hover:border-[#DA7756] hover:shadow-md transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">{prompt.icon}</span>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-semibold text-[#1A1A1A] group-hover:text-[#DA7756] transition-colors">
                        {prompt.title}
                      </h3>
                      <p className="text-xs text-[#666666] mt-1 line-clamp-2">
                        {prompt.prompt}
                      </p>
                      <div className="mt-2">
                        <span className="text-xs text-[#999999] bg-[#F5F4F2] px-2 py-1 rounded">
                          {prompt.category}
                        </span>
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#E5E5E5] bg-[#FAFAFA]">
          <p className="text-xs text-[#999999] text-center">
            💡 Click any prompt to use it as a template
          </p>
        </div>
      </div>
    </>
  );
};

export default PromptLibrary;
