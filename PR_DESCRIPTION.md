## Description

Fixed Black formatting and linting issues that were causing CI failures. Applied automatic formatting and added missing type annotations to ensure code meets project standards.

## Type of Change

- [x] **fix**: A bug fix
- [x] **style**: Changes that do not affect the meaning of the code

## Scope

**Scope:** `projects`, `auth`

## Breaking Changes

- [ ] Yes (describe below)
- [x] No

## Testing

- [x] Unit tests pass
- [ ] Integration tests pass
- [x] Manual testing completed
- [x] All existing functionality works as expected

## Checklist

- [x] My code follows the project's style guidelines
- [x] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [x] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [x] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published in downstream modules

## Screenshots (if applicable)

N/A

## Additional Notes

- Applied Black formatter to resolve CI failures
- Added type annotations to ProjectManager class
- Fixed import sorting with isort
- Added missing EOF newlines
- All pre-commit hooks now pass locally

## Related Issues

Fixes CI pipeline failures on main branch
