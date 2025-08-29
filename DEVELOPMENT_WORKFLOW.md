# Development Workflow

This document outlines the development workflow for the Satellite Imagery Gateway project.

## 🚀 Getting Started

### Prerequisites
- Python 3.13+
- Git
- GitHub account

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd satimageAPI

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the development server
python -m app.main
```

## 🔄 Development Workflow

### 1. Create a Feature Branch

**Never work directly on the `main` branch!**

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create and switch to a new feature branch
git checkout -b feat/your-feature-name
# or
git checkout -b fix/bug-description
# or
git checkout -b docs/update-readme
```

### 2. Make Your Changes

- Write your code following the project's style guidelines
- Write tests for new functionality
- Update documentation as needed
- Follow the commit message conventions

### 3. Commit Your Changes

Use the conventional commit format:

```bash
# Stage your changes
git add .

# Commit with proper format
git commit -m "feat: add user registration endpoint"
git commit -m "fix(auth): resolve password verification issue"
git commit -m "docs: update API documentation"
```

### 4. Push and Create Pull Request

```bash
# Push your branch to remote
git push origin feat/your-feature-name

# Create a Pull Request on GitHub
# Use the PR template and fill out all required fields
```

### 5. Code Review Process

1. **Self-Review**: Review your own code before requesting review
2. **Peer Review**: Request review from team members
3. **Address Feedback**: Make requested changes and push updates
4. **Approval**: Get approval from at least one reviewer
5. **Merge**: Once approved, merge the PR

## 📝 Commit Message Examples

### Features
```bash
git commit -m "feat: add satellite imagery search functionality"
git commit -m "feat(auth): implement refresh token system"
git commit -m "feat(api): add image processing endpoints"
```

### Bug Fixes
```bash
git commit -m "fix: resolve authentication token expiration"
git commit -m "fix(auth): correct password hash verification"
git commit -m "fix(api): handle missing email validation"
```

### Documentation
```bash
git commit -m "docs: add API usage examples"
git commit -m "docs: update installation instructions"
git commit -m "docs: include authentication flow diagram"
```

### Refactoring
```bash
git commit -m "refactor: reorganize service layer structure"
git commit -m "refactor(auth): extract password validation logic"
git commit -m "refactor(api): simplify endpoint response handling"
```

## 🧪 Testing

### Run Tests Locally
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run tests with verbose output
pytest -v
```

### Code Quality Checks
```bash
# Install linting tools
pip install flake8 black isort mypy

# Check code style
flake8 app/
black --check app/
isort --check-only app/

# Type checking
mypy app/
```

## 🔒 Branch Protection Rules

The `main` branch is protected with the following rules:

- ✅ **Requires pull request reviews** before merging
- ✅ **Requires status checks** to pass (tests, linting, security)
- ✅ **Requires branches to be up to date** before merging
- ✅ **Prevents direct pushes** to main
- ✅ **Requires linear history** (no merge commits)

## 🚨 What Happens If You Try to Push to Main

```bash
# This will FAIL
git push origin main

# Error: remote: error: GH006: Protected branch update failed for refs/heads/main.
# remote: error: At least 1 approving review is required by reviewers with write access.
```

## 📋 Pull Request Checklist

Before submitting a PR, ensure:

- [ ] All tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] Branch is up to date with main
- [ ] PR description is complete
- [ ] Appropriate labels are added

## 🔄 Updating Your Branch

If your branch becomes outdated:

```bash
# Switch to your feature branch
git checkout feat/your-feature-name

# Update main
git checkout main
git pull origin main

# Rebase your feature branch on main
git checkout feat/your-feature-name
git rebase main

# Resolve any conflicts if they occur
# Then force push (since rebase rewrites history)
git push --force-with-lease origin feat/your-feature-name
```

## 🎯 Best Practices

1. **Keep branches focused**: One feature/fix per branch
2. **Write descriptive commit messages**: Clear and concise
3. **Test thoroughly**: Don't submit untested code
4. **Update documentation**: Keep docs in sync with code
5. **Review your own code**: Self-review before requesting review
6. **Respond to feedback**: Address review comments promptly
7. **Keep branches small**: Large PRs are harder to review

## 🆘 Getting Help

- **Code Review**: Ask team members for help
- **Technical Issues**: Check existing issues or create new ones
- **Workflow Questions**: Refer to this document or ask the team
- **Git Issues**: Use `git help <command>` or ask for assistance

## 📚 Additional Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Pull Request Best Practices](https://github.com/thoughtbot/guides/tree/master/code-review)
