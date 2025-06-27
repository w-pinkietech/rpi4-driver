# Development Process Documentation

This directory contains all development process and workflow documentation for the RPi4 Interface Drivers project.

## 📚 Document Index

### Development Guidelines
- **[DEVELOPMENT_RULES.md](DEVELOPMENT_RULES.md)** - 開発ルールブック (Development Rulebook)
  - Development principles and philosophy
  - Git/GitHub workflow rules
  - Coding standards and conventions
  - Testing requirements

### Pull Request Process
- **[PR_GUIDELINES.md](PR_GUIDELINES.md)** - Pull Request submission guidelines
  - PR philosophy based on t-wada's approach
  - Submission checklist
  - Code review process

### Tool-Specific Guidelines
- **[CLAUDE.md](../../CLAUDE.md)** - Claude AI assistant instructions (located at project root)
  - Project overview for AI assistance
  - Supported interfaces and requirements
  - Testing commands and Docker device access
- **[CLAUDE_COLLABORATION.md](CLAUDE_COLLABORATION.md)** - Claude AI collaboration guidelines
  - Guidelines for epic-level discussions
  - Best practices for AI-assisted development
  - When and how to mention Claude in issues/PRs

## 🎯 Process Principles

1. **Quality First** - Following t-wada's philosophy on design and testing
2. **Humble Approach** - Maintaining humility in PR submissions
3. **Clear Communication** - Well-documented code and commit messages
4. **Continuous Improvement** - Regular feedback and iteration

## 📋 Quick Reference

### Testing Commands
```bash
# Run tests
python -m pytest tests/

# Lint code
python -m flake8 src/

# Type check
python -m mypy src/
```

### Git Workflow
- Feature branches from `main`
- Clear, descriptive commit messages
- PR reviews before merging
- Follow semantic versioning

## 🌐 Language Note

Some documents in this directory are written in Japanese (日本語) to accommodate our diverse development team. Key concepts are typically provided in both languages where appropriate.