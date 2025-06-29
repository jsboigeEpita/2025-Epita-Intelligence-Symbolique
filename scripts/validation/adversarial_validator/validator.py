from typing import Callable, List, Dict, Any
import re


class MultiLevelValidator:
    """
    Multi-level input validator (syntactic, semantic, logical, security).
    """
    def __init__(self, validators: List[Callable[[str], Dict[str, Any]]]):
        self.validators = validators

    def validate(self, prompt: str) -> Dict[str, Any]:
        results = []
        for validator in self.validators:
            results.append(validator(prompt))
        passed = all(r.get("passed", True) for r in results)
        return {"passed": passed, "details": results}

def heuristic_validator(prompt: str) -> Dict[str, Any]:
    """
    Validate a prompt based on heuristic factors (length, forbidden patterns, suspicious keywords, entropy, etc).
    Returns a dict with validation results, explanations, and a risk score between 0 (safe) and 1 (very risky).
    """
    import math

    # Syntactic checks
    syntactic_issues = []
    syntactic_score = 0.0
    if len(prompt) > 10000:
        syntactic_issues.append("Prompt too long")
        syntactic_score += 0.2
    forbidden_patterns = [
        r'<script>', r'<\?php', r'\${', r'#{', r'<!--', r'base64,', r'0x[0-9a-fA-F]+', r'[\x00-\x1f\x7f-\x9f]',
        r'os\.system', r'eval\(', r'exec\(', r'subprocess', r'pickle\.loads', r'__import__', r'open\(', r'write\('
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            syntactic_issues.append(f"Forbidden pattern detected: {pattern}")
            syntactic_score += 0.1

    # Suspicious keywords and adversarial patterns (expanded)
    suspicious_keywords = [
        "ignore previous instructions", "jailbreak", "developer mode", "admin mode", "bypass", "unrestricted",
        "system prompt", "simulate", "roleplay", "act as", "hypothetical", "fictional", "override", "disable safety",
        "as an ai", "as a language model", "confidential", "secret", "private", "leak", "reveal", "hidden",
        "prompt injection", "dan mode", "do anything now", "output raw", "no filter", "no censorship", "uncensored",
        "write malware", "generate exploit", "hack", "phishing", "social engineering", "backdoor", "payload",
        "base64 decode", "shell command", "sudo", "root access", "admin password", "bypass restrictions",
        "simulate system", "simulate user", "simulate admin", "simulate developer", "simulate assistant",
        "simulate unrestricted", "simulate dan", "simulate gpt", "simulate openai", "simulate chatgpt"
    ]
    semantic_issues = []
    semantic_score = 0.0
    for keyword in suspicious_keywords:
        if keyword.lower() in prompt.lower():
            semantic_issues.append(f"Suspicious keyword detected: {keyword}")
            semantic_score += 0.03

    # Regex-based adversarial patterns (prompt injection, jailbreak, etc.)
    adversarial_patterns = [
        r'ignore\s+(?:previous|all|your)\s+instructions',
        r'you\s+are\s+now\s+(?:a|an)\s+\w+',
        r'pretend\s+(?:to\s+be|you\s+are)',
        r'role[\s\-]?play\s+as',
        r'imagine\s+(?:you\s+are|that\s+you)',
        r'in\s+a\s+(?:hypothetical|fictional)\s+world',
        r'developer\s+mode',
        r'admin\s+mode',
        r'bypass\s+(?:safety|security|restrictions)',
        r'jailbreak\s+(?:mode|prompt)',
        r'dan\s+(?:mode|prompt)',
        r'unrestricted\s+(?:mode|ai|assistant)',
        r'output\s+raw',
        r'no\s+filter',
        r'no\s+censorship',
        r'uncensored',
        r'write\s+malware',
        r'generate\s+exploit',
        r'phishing',
        r'social\s+engineering',
        r'backdoor',
        r'payload',
        r'base64\s+decode',
        r'shell\s+command',
        r'sudo',
        r'root\s+access',
        r'admin\s+password',
        r'prompt\s+injection',
        r'leak\s+data',
        r'reveal\s+secret',
        r'confidential\s+information'
    ]
    adversarial_issues = []
    adversarial_score = 0.0
    for pattern in adversarial_patterns:
        matches = list(re.finditer(pattern, prompt, re.IGNORECASE))
        if matches:
            adversarial_issues.append(f"Adversarial pattern detected: {pattern} ({len(matches)} match{'es' if len(matches) > 1 else ''})")
            adversarial_score += 0.05 * len(matches)

    # Entropy check (very low entropy may indicate copy-paste or template attack)
    def shannon_entropy(s):
        if not s:
            return 0.0
        prob = [float(s.count(c)) / len(s) for c in set(s)]
        return -sum([p * math.log(p + 1e-10) / math.log(2) for p in prob])
    entropy = shannon_entropy(prompt)
    entropy_pass = entropy > 2.5  # Arbitrary threshold for English text
    entropy_score = 0.0 if entropy_pass else 0.1
    entropy_issue = None if entropy_pass else f"Low entropy detected: {entropy:.2f}"


    # Aggregate risk score (clipped to [0, 1])
    risk_score = syntactic_score + semantic_score + adversarial_score + entropy_score
    risk_score = min(risk_score, 1.0)

    # Pass if risk_score < threshold (e.g. 0.5)
    threshold = 0.5
    passed = risk_score < threshold

    # Collect all issues
    issues = syntactic_issues + semantic_issues + adversarial_issues 
    if not entropy_pass and entropy_issue:
        issues.append(entropy_issue)

    return {
        "level": "heuristic",
        "passed": passed,
        "risk_score": risk_score,
        "syntactic_issues": syntactic_issues,
        "semantic_issues": semantic_issues,
        "adversarial_issues": adversarial_issues,
        "entropy": entropy,
        "entropy_pass": entropy_pass,
        "issues": issues,
        "threshold": threshold
    }