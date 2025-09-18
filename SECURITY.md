# 🔒 Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | ✅ Yes            |
| < 1.0   | ❌ No             |

## 🛡️ Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in YT Music Downloader, please report it responsibly.

### 📧 How to Report

**Please do NOT open a public issue for security vulnerabilities.**

Instead, please:

1. **Email us** at: [charlie.act7@gmail.com] (charlie.act7@gmail.com)
2. **Use GitHub Security Advisories**: Go to the repository → Security tab → "Report a vulnerability"

### 📋 What to Include

When reporting a vulnerability, please include:

- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Affected versions**
- **Potential impact** and severity
- **Suggested fix** (if you have one)
- **Your contact information** for follow-up

### ⏱️ Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Status Updates**: Weekly until resolved
- **Fix Release**: Depending on severity (see below)

### 🚨 Severity Levels

| Severity | Description | Response Time |
|----------|-------------|---------------|
| **Critical** | Remote code execution, privilege escalation | 24-48 hours |
| **High** | Data exposure, authentication bypass | 1 week |
| **Medium** | Limited data exposure, DoS | 2 weeks |
| **Low** | Information disclosure, minor issues | 1 month |

## 🔍 Security Considerations

### Data Handling
YT Music Downloader:
- ✅ **Does NOT** collect or transmit personal data
- ✅ **Does NOT** store user credentials
- ✅ **Does NOT** connect to external servers (except YouTube for downloads)
- ✅ Stores only local configuration in `~/.ytmusic-dl.json`

### File System Access
The application:
- ✅ Only writes to user-specified directories
- ✅ Validates file paths to prevent directory traversal
- ✅ Uses safe file naming conventions
- ⚠️ Requires write access to download directories (user-controlled)

### Network Security
- ✅ Uses HTTPS for all YouTube connections
- ✅ Validates SSL certificates
- ✅ No custom network protocols
- ✅ Relies on yt-dlp's security mechanisms

### Dependencies
We regularly monitor dependencies for vulnerabilities:
- **yt-dlp**: Core download functionality
- **typer**: CLI framework
- **rich**: Terminal UI
- **psutil**: System information

## 🛠️ Security Best Practices for Users

### Safe Usage
1. **Download from trusted sources** only
2. **Keep dependencies updated** regularly
3. **Use antivirus software** to scan downloaded files
4. **Don't run as administrator** unless necessary
5. **Be cautious with playlist URLs** from untrusted sources

### Configuration Security
- ✅ Configuration file contains only local paths and preferences
- ✅ No sensitive credentials are stored
- ⚠️ Be careful with output directory permissions

### Network Security
- ✅ Only connects to YouTube/Google domains
- ✅ Uses standard HTTPS protocols
- ⚠️ Corporate firewalls may need YouTube access

## 🔧 Security Features

### Input Validation
- ✅ URL validation and sanitization
- ✅ File path validation
- ✅ Configuration parameter validation
- ✅ Prevents path traversal attacks

### Error Handling
- ✅ Graceful error handling
- ✅ No sensitive information in error messages
- ✅ Safe fallback behaviors

### File Operations
- ✅ Safe file naming (no dangerous characters)
- ✅ Atomic file operations where possible
- ✅ Proper cleanup of temporary files

## 🚫 Known Limitations

### Not Security Issues
These are known limitations, not security vulnerabilities:

1. **YouTube API Changes**: May break functionality but don't pose security risks
2. **Copyright Claims**: Content restrictions are enforced by YouTube
3. **Network Connectivity**: Requires internet access to function
4. **File System Access**: Needs write permissions for downloads (by design)

### Out of Scope
The following are outside our security scope:

- **YouTube's security**: We rely on YouTube's infrastructure
- **Operating system security**: System-level vulnerabilities
- **Third-party plugins**: Not officially supported
- **Copyright violations**: User responsibility

## 📜 Legal and Compliance

### Usage Compliance
Users are responsible for:
- ✅ Complying with YouTube's Terms of Service
- ✅ Respecting copyright laws
- ✅ Following local regulations
- ✅ Using downloaded content appropriately

### Data Protection
- ✅ No personal data collection
- ✅ No data transmission to third parties
- ✅ Local-only configuration storage
- ✅ GDPR compliant (no data processing)

## 🔄 Security Updates

### Update Notifications
- Watch this repository for security releases
- Check release notes for security-related changes
- Subscribe to GitHub Security Advisories

### Applying Updates
```bash
# Update to latest version
git pull origin main
pip install -r requirements.txt --upgrade

# Or if installed via pip
pip install --upgrade yt-music-downloader
```

## 🤝 Security Community

### Responsible Disclosure
We follow responsible disclosure practices:
- ✅ Private reporting of vulnerabilities
- ✅ Coordinated public disclosure
- ✅ Credit to security researchers
- ✅ Transparent communication

### Security Research
We welcome security research and testing:
- 🔍 Static code analysis
- 🔍 Dependency vulnerability scanning
- 🔍 Penetration testing (on your own systems)
- 🔍 Code review contributions

## 📞 Contact Information

For security-related inquiries:
- **Security Email**: [Create a security email]
- **GitHub Security**: Use repository's Security tab
- **General Issues**: Use GitHub Issues (for non-security bugs)

---

## 🙏 Acknowledgments

We thank the security community and researchers who help keep YT Music Downloader secure.

**Security Hall of Fame:**
<!-- List security researchers who have contributed -->
- [Your name could be here]

---

*This security policy is effective as of the latest commit date and may be updated as needed.*