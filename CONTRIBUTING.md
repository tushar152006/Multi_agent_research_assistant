# Contributing to Multi-Agent Research Assistant

Thank you for your interest in contributing to the **Multi-Agent Research Assistant**! We welcome contributions from developers, researchers, and AI practitioners.

---

## 🧭 Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone. Please treat all contributors and maintainers with courtesy and respect.

---

## 🛠️ Development Setup

### 1. Prerequisites
- **Python**: 3.11+ (recommended)
- **Node.js**: 20+ & npm 10+
- **Git**: 2.30+
- *(Optional)* **Docker & Docker Compose**: For containerized development

### 2. Fork & Clone
```bash
git clone https://github.com/tushar152006/Multi_agent_research_assistant.git
cd Multi_agent_research_assistant
```

### 3. Backend Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
pip install pytest pytest-asyncio ruff
```

### 4. Frontend Setup
```bash
cd frontend
npm install
cd ..
```

---

## 🧪 Running Tests & Quality Checks

Before submitting any Pull Request, ensure that all tests and linting checks pass:

### Backend Unit Tests
```bash
# Run tests with unittest (100% offline, zero API keys required)
python -m unittest discover -s backend/tests -p "test_*.py"
```

### Frontend Typecheck & Build
```bash
cd frontend
npx tsc --noEmit
npm run build
cd ..
```

---

## 🌿 Branching & Commit Conventions

1. Create a feature branch with a descriptive name:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```
2. Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` A new feature or capability
   - `fix:` A bug fix
   - `docs:` Documentation updates
   - `test:` Adding or updating tests
   - `refactor:` Code change that neither fixes a bug nor adds a feature
   - `chore:` Build scripts, dependency updates, CI configurations

---

## 📤 Submitting a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feat/your-feature-name
   ```
2. Open a Pull Request against the `main` branch.
3. Fill in the Pull Request template detailing your changes, verification steps, and any linked issues.
4. Ensure CI checks pass on GitHub Actions.
