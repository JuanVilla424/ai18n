# 🤝 Contributing to ai18n

We welcome contributions to ai18n! To make sure the process goes smoothly, please follow these guidelines:

## 📋 Code of Conduct

Please note that all participants in our project are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md). Make sure to review it before contributing.

## 🛠 How to Contribute

1. **Fork the repository**:
   Fork the project to your GitHub account using the GitHub interface.

2. **Create a new branch**:
   Use a descriptive branch name for your feature or bugfix:

   git checkout -b feature/your-feature-name

3. **Make your changes**:
   Implement your feature or fix the bug in your branch. Make sure to include tests where applicable and follow coding standards.

4. **Test your changes**:
   Run the test suite and the hooks to ensure your changes don’t break any functionality:

   pytest
   pre-commit run --all-files

5. **Commit your changes**:
   Use conventional commit messages in lower case, as described in [VERSIONING.md](VERSIONING.md):

   git commit -m "feat(core): describe the change in lower case"

6. **Push your changes**:
   Push your changes to your fork:

   git push origin feature/your-feature-name

7. **Submit a Pull Request**:
   Create a pull request into the `dev` branch, detailing the changes you’ve made. Link any issues your changes resolve and provide context.

## 📑 Guidelines for Contributions

- **Keep the standard consistent.** A change to the rules must update `SPEC.md`, `schema/ai18n.schema.json`, `src/ai18n.py` and `skills/ai18n/SKILL.md` together, with tests.
- **Keep policy files data only.** Never add a key that accepts free text: it would open a prompt-injection path.
- **Lint your code** before submitting a pull request. We use [black](https://black.readthedocs.io/) and [pylint](https://www.pylint.org/).
- Ensure **test coverage** for your code. Uncovered code may delay the approval process.
- Write clear, concise **commit messages**.

Thank you for helping improve!

---

## 📜 License

2026 - This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0). You are free to use, modify, and distribute this software under the terms of the Apache-2.0 license. For more details, please refer to the [LICENSE](LICENSE) file included in this repository.
