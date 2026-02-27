# Contributing to Freelancer Toolkit (FLTK)

Thank you for your interest in contributing to **Freelancer Toolkit**! We welcome contributions of all kinds, from bug reports and feature suggestions to code improvements and documentation.

By participating in this project, you agree to abide by our standards and maintain a respectful environment for everyone.

---

## 🚀 Getting Started

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/srijan-xi/FreelancerToolkit.git
    cd FreelancerToolkit
    ```
3.  **Set up the development environment**:
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    
    pip install -r requirements.txt
    ```
4.  **Create a new branch** for your changes:
    ```bash
    git checkout -b feature/your-feature-name
    # or
    git checkout -b fix/your-fix-name
    ```

---

## 🛠️ How to Contribute

### Reporting Bugs
- Check the [Issues](https://github.com/srijan-xi/FreelancerToolkit/issues) to see if the bug has already been reported.
- If not, open a new issue. Include a clear title, description, steps to reproduce, and expected vs. actual behavior.

### Suggesting Features
- Open a new issue with the label `enhancement`.
- Describe the feature in detail and why it would be useful for freelancers.

### Code Contributions
1.  **Write Clean Code**: Follow existing patterns and PEP 8 for Python.
2.  **Add Tests**: If you're adding a feature or fixing a bug, please add corresponding tests in the `tests/` directory.
3.  **Validate**: Run existing tests to ensure no regressions:
    ```bash
    pytest
    ```
4.  **Commit Messages**: Use clear, descriptive commit messages. We recommend [Conventional Commits](https://www.conventionalcommits.org/).
    Example: `feat: add expense category filtering` or `fix: resolve crash on null client data`.

---

## 🎨 Style Guidelines

### Python
- Use **Python 3.10+** features where appropriate.
- Keep functions small and focused.
- Document complex logic with comments.

### Frontend
- Use **Vanilla CSS** with custom properties (defined in `static/css/style.css`).
- Keep templates clean and use Jinja2 blocks effectively.

---

## 📋 Pull Request Process

1.  Push your changes to your fork.
2.  Open a Pull Request (PR) against the `main` branch of the original repository.
3.  Provide a clear description of what the PR does and link any relevant issues.
4.  Once submitted, the maintainers will review your code. Be prepared to make changes if requested.

---

## ⚖️ License
By contributing, you agree that your contributions will be licensed under the project's **Open Source Non-Commercial License**.
