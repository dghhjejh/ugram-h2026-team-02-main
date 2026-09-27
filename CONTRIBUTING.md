# Contributing Guide

Matches your desire to help? Awesome! We love contributions from everyone, whether it's fixing a typo, adding a feature, or fixing a bug.

## 🏁 Getting Started

1.  **Fork the repo** on GitHub.
2.  **Clone** your fork locally:
    ```bash
    git clone https://github.com/YOUR-USERNAME/DefaultPython.git
    cd DefaultPython
    ```
3.  **Install Dependencies** (uses `uv`):
    ```bash
    uv sync
    ```

## 🛠️ Making Changes

1.  **Create a Branch**:
    ```bash
    git checkout -b feat/my-new-feature
    ```
2.  **Code Away!**
3.  **Test Your Changes**:
    Run the full suite to make sure nothing broke.
    ```bash
    task test
    ```
4.  **Check Code Quality**:
    Run the linter and formatter.
    ```bash
    task lint
    task format
    ```

## 📝 Committing Changes

We use **Conventional Commits** to keep our history clean and automate releases.
A commit message consists of a **type**, a **scope** (optional), and a **description**.

**Format**: `type(scope): description`

**Common Types**:
*   `feat`: A new feature
*   `fix`: A bug fix
*   `docs`: Documentation only changes
*   `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc)
*   `refactor`: A code change that neither fixes a bug nor adds a feature
*   `test`: Adding missing tests or correcting existing tests
*   `chore`: Changes to the build process or auxiliary tools and libraries

**Example**:
```bash
git commit -m "feat(auth): add google login support"
```

> **Pro Tip**: You can use the `cz` tool (installed automatically) to help you format this:
> ```bash
> uv run cz commit
> ```

## 🚀 Submitting a Pull Request

1.  Push your branch:
    ```bash
    git push origin feat/my-new-feature
    ```
2.  Open a Pull Request on GitHub.
3.  Ensure the CI checks pass (the Actions tab).

Thank you for your contribution!
