# Team Development Guidelines

## Overview

This document defines the development workflow, Git practices, naming conventions, and collaboration rules that all team members must follow throughout the project.

The purpose of these guidelines is to:

- Maintain a clean and organized codebase
- Reduce merge conflicts
- Improve code quality
- Ensure efficient collaboration
- Follow professional software development practices

All team members are expected to follow these guidelines.

---

# 1. Git Workflow Rules

## 1.1 Do Not Commit Directly to Main

Direct commits to the `main` branch are **not allowed**.

The `main` branch should always contain stable and working code.

All changes must follow this workflow:

1. Update your local `main` branch
2. Create a new branch
3. Implement your changes
4. Test your changes locally
5. Push your branch
6. Create a Pull Request (PR)
7. Get reviewed by another team member
8. Merge into `main`

Workflow:

```
main
 |
 |-- create branch
        |
        |-- make changes
        |
        |-- create Pull Request
        |
        |-- review
        |
        |-- merge into main
```

---

## 1.2 Always Pull Latest Changes Before Starting Work

Before creating a new branch, make sure your local repository is updated.

```bash
git checkout main
git pull origin main
```

Always start new work from the latest version of `main`.

---

## 1.3 Keep Branches Focused

Each branch should represent **one specific task or feature**.

Avoid combining unrelated changes.

Example:

Good:

```
ankit/feature/login-system
```

Bad:

```
ankit/feature/login-dashboard-database-fixes
```

---

# 2. Branch Naming Convention

All branches must follow this format:

```
[member-name]/[type]/[description]
```

Rules:

- Use lowercase letters
- Use hyphens (`-`) instead of spaces
- Keep names short but descriptive
- The branch name should clearly explain the purpose

---

## Branch Types

| Type | Purpose |
|---|---|
| feature | Adding new functionality |
| bug | Fixing an existing issue |
| refactor | Improving code structure without changing functionality |
| docs | Documentation changes |
| test | Adding or updating tests |
| config | Configuration changes |
| research | Experimental investigation |
| hotfix | Urgent fixes |

---

## Examples

### Feature Branches

```
ankit/feature/user-authentication
ankit/feature/dashboard-ui
ankit/feature/mqtt-integration
```

### Bug Fix Branches

```
ankit/bug/fix-login-error
ankit/bug/fix-database-connection
```

### Documentation Branches

```
ankit/docs/update-readme
ankit/docs/add-api-documentation
```

### Testing Branches

```
ankit/test/add-unit-tests
```

### Refactoring Branches

```
ankit/refactor/backend-cleanup
```

---

# 3. Commit Guidelines

## 3.1 Write Meaningful Commit Messages

Commit messages should clearly describe what was changed.

Avoid:

```
fixed stuff
changes
update
done
```

Use:

```
Feature: Add vehicle monitoring dashboard
Bug: Fix MQTT connection timeout
Docs: Update installation instructions
Test: Add API integration tests
Refactor: Improve database service structure
```

---

## 3.2 Commit Message Format

Use:

```
<Type>: <Short description>
```

Allowed types:

| Type | Usage |
|---|---|
| Feature | New functionality |
| Bug | Bug fixes |
| Docs | Documentation |
| Test | Testing changes |
| Refactor | Code improvements |
| Config | Configuration changes |

Examples:

```
Feature: Add user registration API
Bug: Fix incorrect sensor data parsing
Docs: Update project setup guide
Refactor: Improve backend architecture
```

---

## 3.3 Make Small and Logical Commits

Avoid large commits containing many unrelated changes.

Good:

```
Commit 1:
Add login API endpoint

Commit 2:
Add authentication validation

Commit 3:
Add login tests
```

Avoid:

```
Added everything
```

---

# 4. Pull Request Rules

## 4.1 All Changes Require a Pull Request

No branch should be merged into `main` without a Pull Request.

Every Pull Request must include:

- Clear title
- Description of changes
- Testing performed
- Screenshots (if UI changes)
- Any known limitations

---

## 4.2 Pull Request Title Format

Use:

```
<Type>: <Description>
```

Examples:

```
Feature: Add real-time dashboard
Bug: Fix API response issue
Docs: Improve installation guide
```

---

## 4.3 Code Review Requirements

Before merging:

- At least one team member must review the PR
- Reviewer should check:
  - Code quality
  - Functionality
  - Possible bugs
  - Testing
  - Documentation

The author must address important review comments before merging.

---

# 5. Code Quality Rules

## 5.1 Before Pushing Code

Ensure:

- Code is formatted properly
- No unused imports exist
- No debug statements remain
- No unnecessary comments exist
- Application runs successfully
- Tests pass

---

## 5.2 Follow Existing Project Structure

Do not:

- Create random folders
- Move files unnecessarily
- Rename major components without discussion

If a structural change is required, discuss it with the team first.

---

## 5.3 Do Not Commit Sensitive Information

Never commit:

- Passwords
- API keys
- Tokens
- Database credentials
- Personal configuration files

Use environment variables instead.

Example:

```
.env
.env.example
```

---

# 6. Dependency Management

Before adding a new dependency:

1. Discuss with the team
2. Explain why it is required
3. Ensure it does not break existing functionality

Update the appropriate dependency file:

| Technology | File |
|---|---|
| Python | requirements.txt |
| Java Maven | pom.xml |
| Gradle | build.gradle |
| Node.js | package.json |

---

# 7. File Naming Convention

Use consistent naming throughout the project.

## General Files

Use:

```
lowercase-with-hyphens
```

Examples:

```
user-service.js
vehicle-controller.java
database-config.py
```

Avoid:

```
UserService.js
my_file.py
New Folder
```

---

## Documentation Files

Use:

```
README.md
ARCHITECTURE.md
API_DOCUMENTATION.md
SETUP_GUIDE.md
```

---

# 8. Testing Rules

Before creating a Pull Request:

Every developer must:

- Run the application locally
- Test their changes
- Verify existing functionality still works
- Add tests for new features when possible

---

# 9. Keeping Branches Updated

Do not wait until the end of development to resolve conflicts.

Regularly update your branch:

```bash
git checkout main
git pull origin main

git checkout your-branch
git merge main
```

Resolve conflicts immediately.

---

# 10. Issue Tracking

For major tasks:

1. Create or assign an issue
2. Describe the task clearly
3. Assign responsible team member
4. Link the branch to the issue

Example:

Issue:

```
#24 Add MQTT data processing
```

Branch:

```
ankit/feature/mqtt-data-processing
```

---

# 11. Repository Cleanliness

Do not commit generated or unnecessary files.

Examples:

```
node_modules/
target/
build/
dist/
.env
.DS_Store
temporary files
logs/
```

Ensure `.gitignore` is updated properly.

---

# 12. Hotfix Rules

For urgent fixes:

Create:

```
[member-name]/hotfix/[description]
```

Example:

```
ankit/hotfix/fix-critical-error
```

After completing:

1. Test the fix
2. Create PR
3. Get review
4. Merge
5. Update other branches

---

# 13. Communication Rules

Before making major changes, communicate with the team.

Examples:

- Changing architecture
- Changing database design
- Adding major dependencies
- Changing APIs
- Refactoring large modules

Avoid making changes that affect others without discussion.

---

# 14. Final Checklist Before Merging

Before merging a Pull Request, confirm:

- [ ] Branch follows naming convention
- [ ] Code has been tested
- [ ] No sensitive information is included
- [ ] Commit messages are meaningful
- [ ] Documentation is updated if required
- [ ] Another team member has reviewed the changes
- [ ] No merge conflicts exist

---

# Golden Rules

Always remember:

✅ Never commit directly to `main`  
✅ Create a branch for every change  
✅ Keep commits small and meaningful  
✅ Review code before merging  
✅ Communicate major changes  
✅ Keep the repository clean  
✅ Test before pushing  
✅ Respect teammates' work  

Following these guidelines will help maintain a professional and efficient development workflow.