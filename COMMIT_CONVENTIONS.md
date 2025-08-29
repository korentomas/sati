# Commit Message Conventions

This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.

## Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Types

### Primary Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to the build process or auxiliary tools and libraries such as documentation generation

### Additional Types

- **ci**: Changes to CI configuration files and scripts
- **build**: Changes that affect the build system or external dependencies
- **revert**: Reverts a previous commit

## Examples

### Feature
```
feat: add user authentication system
feat(auth): implement JWT token validation
feat(api): add satellite imagery search endpoint
```

### Bug Fix
```
fix: resolve authentication token expiration issue
fix(auth): correct password hash verification
fix(api): handle missing email validation dependency
```

### Documentation
```
docs: update API documentation with authentication examples
docs: add setup instructions for development environment
docs: include commit message conventions
```

### Refactoring
```
refactor: reorganize authentication service structure
refactor(auth): extract password validation logic
refactor(api): simplify endpoint response handling
```

### Performance
```
perf: optimize database queries in user service
perf(auth): improve JWT token generation speed
```

### Testing
```
test: add unit tests for authentication service
test(auth): cover password verification edge cases
test(api): validate protected endpoint access
```

### Chores
```
chore: update dependencies to latest versions
chore: add .gitignore for Python projects
chore: configure pre-commit hooks
```

## Scope

The scope is optional and should be the name of the component affected (e.g., `auth`, `api`, `core`, `docs`).

## Breaking Changes

Breaking changes should be indicated by adding `!` after the type/scope and `BREAKING CHANGE:` in the footer:

```
feat!: change authentication endpoint response format

BREAKING CHANGE: The login endpoint now returns a different token structure
```

## Guidelines

1. **Use imperative mood**: "add" not "added" or "adds"
2. **Don't capitalize the first letter**: "feat:" not "Feat:"
3. **No period at the end**: "feat: add authentication" not "feat: add authentication."
4. **Keep it concise**: The description should be clear and brief
5. **Be specific**: "fix: resolve 403 error in profile endpoint" not "fix: fix bug"

## Examples in Context

```
feat: add user authentication system

- Implement JWT-based authentication
- Add login/logout endpoints
- Include password hashing with bcrypt
- Add protected route middleware

Closes #123
```

```
fix(auth): resolve password verification issue

The bcrypt hash was corrupted, causing authentication failures.
Updated with fresh hash for test user credentials.

Fixes #456
```
