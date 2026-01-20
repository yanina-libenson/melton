#!/usr/bin/env python3
"""
Generate secure secrets for production deployment.
Use these values in your Render environment variables.
"""

import secrets

def generate_secret_key(length: int = 64) -> str:
    """Generate a secure random secret key."""
    return secrets.token_urlsafe(length)

def main():
    print("=" * 70)
    print("Melton Production Secrets Generator")
    print("=" * 70)
    print()
    print("Copy these values to your Render.com environment variables:")
    print()
    print("-" * 70)
    print("SECRET_KEY:")
    print(generate_secret_key(64))
    print()
    print("-" * 70)
    print("ENCRYPTION_KEY:")
    print(generate_secret_key(64))
    print()
    print("-" * 70)
    print()
    print("⚠️  IMPORTANT:")
    print("- Store these securely in your password manager")
    print("- Never commit these to git")
    print("- Use these exact values in Render environment variables")
    print("- Generate new keys if these are ever compromised")
    print()

if __name__ == "__main__":
    main()
