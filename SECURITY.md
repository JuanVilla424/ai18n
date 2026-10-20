# 🔒 Security Policy

Security Policy for the **ai18n** repository: the specification, the JSON Schema, the reference resolver and the Agent Skill.

## 🧮 Supported Versions

We provide security updates for the following versions of our project:

| Version | Status    | Secure |
| ------- | --------- | ------ |
| 1.x     | Supported | Yes    |

## 🛡️ Security Practices

- Policy files are data only: the schema admits fixed keys, language tags, and globs and catalog patterns with a restricted alphabet, so a policy file cannot carry instructions for a model.
- Engines inject the normalized rendering of a policy, never the raw file, so comments never reach a model.
- An invalid policy is rejected as a whole and never resolved in part. A file with a repeated key, or larger than 64 KiB, is invalid.
- Message catalogs are read only to be checked, never injected. A catalog larger than 5 MiB, nested more than 32 levels deep or with more than 100,000 entries is reported instead of read.
- Every GitHub Action is pinned to a full commit SHA, and the workflows request only the permissions they use.
- Dependencies are monitored and updated to address known vulnerabilities.

## 📲 Security Updates

- Security updates are released as soon as possible after a vulnerability is confirmed.
- Users are encouraged to update to the latest version to benefit from security fixes.

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability within this project, such as a way to make a valid policy file carry instructions to a model, please follow these steps:

1. **Do not create a public issue.** Instead, contact us directly to responsibly disclose the vulnerability.

2. **Email** [r6ty5r296it6tl4eg5m.constant214@passinbox.com](mailto:r6ty5r296it6tl4eg5m.constant214@passinbox.com) with the following information:
   - A description of the vulnerability.
   - Steps to reproduce the issue.
   - Any potential impact or severity.

3. **Wait for a response.** We will acknowledge your report and work with you to address the issue promptly.

## 🛰️ Additional Resources

- [OWASP Security Guidelines](https://owasp.org/)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

Thank you for helping us keep this project secure!

---

## 📜 License

2026 - This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0). You are free to use, modify, and distribute this software under the terms of the Apache-2.0 license. For more details, please refer to the [LICENSE](LICENSE) file included in this repository.
