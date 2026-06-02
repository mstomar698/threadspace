# Security Policy

## Supported versions

ThreadSpace is in active development; security fixes are applied to the `main`
branch.

## Reporting a vulnerability

Please **do not** report security vulnerabilities through public GitHub issues.

Instead, report them privately via one of:

- GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
  (the **Security** tab > **Report a vulnerability**), or
- email **tomarm698@gmail.com**.

Please include:

- a description of the issue and its impact,
- steps to reproduce (a proof of concept if possible),
- affected component (backend API, frontend, or the Rust realtime gateway).

We will acknowledge your report as soon as we can, keep you updated on progress,
and credit you in the fix unless you prefer to remain anonymous.

## Handling secrets

Never commit real secrets. Local configuration lives in `.env` files (ignored by
git); see `.env.example`, `frontend/.env.example`, and `realtime/.env.example`
for the supported variables.
