#!/usr/bin/env python3
"""Query claude-code RAG system about CLI implementation"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from scripts.query_claude_code import query

def main():
    """Query about CLI tools and patterns"""

    questions = [
        'What CLI tools and frameworks does claude-code use?',
        'How does claude-code handle command line arguments?',
        'What terminal UI libraries does claude-code use?',
        'How does claude-code implement slash commands?',
        'What is the architecture of claude-code CLI?'
    ]

    for i, q in enumerate(questions, 1):
        print('\n' + '='*70)
        print(f'Question {i}: {q}')
        print('='*70)
        query(q, n_results=3)
        print()

if __name__ == '__main__':
    main()
