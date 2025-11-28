#!/usr/bin/env python3
"""
Gemini & CodeRabbit Analyzer
Copies security test results to the target codebase and runs AI analysis
"""

import os
import shutil
import subprocess
import json
from pathlib import Path


# Configuration
SOURCE_DIR = Path(__file__).parent
TARGET_CODEBASE = Path("/Users/a_nick/Documents/AI-Hack/buggy-vibe")
RL_TRAINING_DATA = SOURCE_DIR / "rl_training_data.json"
EXPLOIT_PLAN = SOURCE_DIR / "final_exploit_plan.json"


def copy_files_to_codebase():
    """Copy the training data and exploit plan to the target codebase"""
    print("=" * 60)
    print("Copying Security Test Results to Target Codebase")
    print("=" * 60)
    print()

    # Ensure target directory exists
    if not TARGET_CODEBASE.exists():
        print(f"❌ Error: Target codebase not found at {TARGET_CODEBASE}")
        return False

    # Copy RL training data
    if RL_TRAINING_DATA.exists():
        target_rl_data = TARGET_CODEBASE / "rl_training_data.json"
        shutil.copy2(RL_TRAINING_DATA, target_rl_data)
        print(f"Copied {RL_TRAINING_DATA.name} -> {target_rl_data}")
    else:
        print(f"Warning: {RL_TRAINING_DATA.name} not found")
        return False

    # Copy exploit plan
    if EXPLOIT_PLAN.exists():
        target_exploit_plan = TARGET_CODEBASE / "final_exploit_plan.json"
        shutil.copy2(EXPLOIT_PLAN, target_exploit_plan)
        print(f"Copied {EXPLOIT_PLAN.name} -> {target_exploit_plan}")
    else:
        print(f"Warning: {EXPLOIT_PLAN.name} not found")
        return False

    # Create GEMINI.md file with prompt and file tags
    gemini_md_path = TARGET_CODEBASE / "GEMINI.md"
    gemini_md_content = """# Security Vulnerabilities Found

These issues were found in this codebase. See if you can work on them.

@final_exploit_plan.json @rl_training_data.json
"""

    with open(gemini_md_path, 'w') as f:
        f.write(gemini_md_content)
    print(f"Created GEMINI.md with prompt and file tags")

    # Create coderabbit.yaml configuration file
    coderabbit_yaml_path = TARGET_CODEBASE / ".coderabbit.yaml"
    coderabbit_yaml_content = """# yaml-language-server: $schema=https://coderabbit.ai/integrations/schema.v2.json
language: en-US
tone_instructions: 'Focus on security vulnerabilities and provide actionable fixes. Be direct and thorough in security assessments.'
early_access: false
enable_free_tier: true
reviews:
  profile: assertive
  request_changes_workflow: true
  high_level_summary: true
  high_level_summary_placeholder: '@coderabbitai summary'
  auto_title_placeholder: '@coderabbitai'
  review_status: true
  commit_status: true
  poem: false
  collapse_walkthrough: false
  sequence_diagrams: false
  changed_files_summary: true
  labeling_instructions:
    - 'security: Files that address security vulnerabilities'
    - 'xss-fix: Changes that fix XSS vulnerabilities'
    - 'sql-injection-fix: Changes that fix SQL injection vulnerabilities'
  path_filters:
    - '**/*'
    - '!**/node_modules/**'
    - '!**/.git/**'
    - '!**/dist/**'
    - '!**/build/**'
  path_instructions:
    - path: '**/*.{js,jsx,ts,tsx}'
      instructions: |
        - Review all user input handling for XSS vulnerabilities
        - Check if input sanitization is properly implemented
        - Validate that dangerouslySetInnerHTML is never used with user input
        - Ensure proper escaping of HTML entities
        - Review for SQL injection vulnerabilities in any database queries
        - Check for proper parameterized queries or ORM usage
        - Validate input validation on all user-facing fields
        - Reference @final_exploit_plan.json for specific vulnerabilities found
        - Reference @rl_training_data.json for exploit patterns detected
    - path: '**/App.{js,jsx,ts,tsx}'
      instructions: |
        - This is the main application component
        - Ensure all user input is properly sanitized before rendering
        - Check that form submissions use proper CSRF protection
        - Validate that state management doesn't expose sensitive data
        - Review component props for potential XSS vectors
    - path: '**/*Component.{js,jsx,ts,tsx}'
      instructions: |
        - Review component for unsafe rendering of user input
        - Check prop validation and sanitization
        - Ensure no direct HTML injection from props
        - Validate event handlers don't execute unsanitized user input
    - path: '**/*.html'
      instructions: |
        - Review for inline script tags that might execute user input
        - Check for missing Content-Security-Policy headers
        - Validate that forms have proper input validation attributes
        - Look for missing or weak XSS protection
  abort_on_close: true
  auto_review:
    enabled: true
    auto_incremental_review: true
    ignore_title_keywords: []
    labels: []
    drafts: false
    base_branches:
      - 'main'
      - 'master'
  tools:
    shellcheck:
      enabled: true
    markdownlint:
      enabled: true
    github-checks:
      enabled: true
      timeout_ms: 90000
    languagetool:
      enabled: true
      enabled_only: false
      level: default
    biome:
      enabled: true
    eslint:
      enabled: true
    gitleaks:
      enabled: true
    semgrep:
      enabled: true
    actionlint:
      enabled: true
    ast-grep:
      packages: []
      rule_dirs: []
      util_dirs: []
      essential_rules: true
chat:
  auto_reply: true
knowledge_base:
  opt_out: false
  learnings:
    scope: auto
  issues:
    scope: auto
  pull_requests:
    scope: auto
"""

    with open(coderabbit_yaml_path, 'w') as f:
        f.write(coderabbit_yaml_content)
    print(f"Created .coderabbit.yaml with security-focused configuration")

    print()
    return True


def run_gemini_analysis():
    """Run Gemini CLI interactively"""
    print("=" * 60)
    print("Running Gemini AI Analysis")
    print("=" * 60)
    print()

    print(f"Working directory: {TARGET_CODEBASE}")
    print(f"GEMINI.md file created with prompt and file tags")
    print(f"   You can reference it with @GEMINI.md or manually tag the files")
    print()
    print("-" * 60)
    print()

    try:
        # Change to target directory
        original_dir = os.getcwd()
        os.chdir(TARGET_CODEBASE)

        # Run gemini CLI - plain and simple
        result = os.system('gemini')

        # Return to original directory
        os.chdir(original_dir)

        print()
        print("Gemini session ended")
        return result == 0
    except Exception as e:
        print(f"Error running Gemini: {e}")
        return False


def run_coderabbit_analysis():
    """Run CodeRabbit CLI interactively after Gemini"""
    print()
    print("=" * 60)
    print("Running CodeRabbit Analysis")
    print("=" * 60)
    print()

    print(f"Working directory: {TARGET_CODEBASE}")
    print()
    print("Opening CodeRabbit CLI - you have full control!")
    print()
    print("-" * 60)
    print()

    try:
        # Change to target directory
        original_dir = os.getcwd()
        os.chdir(TARGET_CODEBASE)

        # Run coderabbit interactively - it will inherit stdin/stdout/stderr
        result = os.system('coderabbit')

        # Return to original directory
        os.chdir(original_dir)

        print()
        print("CodeRabbit session ended")
        return result == 0
    except Exception as e:
        print(f"Error running CodeRabbit: {e}")
        return False


def display_summary():
    """Display summary of the files being analyzed"""
    print("=" * 60)
    print("Security Test Results Summary")
    print("=" * 60)
    print()

    # Load and display summary of RL training data
    if RL_TRAINING_DATA.exists():
        with open(RL_TRAINING_DATA, 'r') as f:
            rl_data = json.load(f)
            print(f"RL Training Data: {len(rl_data)} actions recorded")

            # Count unique exploit types
            xss_count = sum(1 for item in rl_data if 'XSS' in item.get('reason', ''))
            sql_count = sum(1 for item in rl_data if 'SQL' in item.get('reason', ''))
            print(f"   - XSS attempts: {xss_count}")
            print(f"   - SQL injection attempts: {sql_count}")

    print()

    # Load and display summary of exploit plan
    if EXPLOIT_PLAN.exists():
        with open(EXPLOIT_PLAN, 'r') as f:
            exploit_plan = json.load(f)
            exploits = exploit_plan.get('exploits', [])
            print(f"🎯 Exploit Plans: {len(exploits)} exploits identified")
            for i, exploit in enumerate(exploits, 1):
                reason = exploit.get('reason', 'Unknown')
                print(f"   {i}. {reason}")

    print()


def main():
    """Main execution function"""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "Gemini & CodeRabbit Security Analyzer" + " " * 10 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Display summary first
    display_summary()

    # Step 1: Copy files
    if not copy_files_to_codebase():
        print("Failed to copy files. Exiting.")
        return 1

    # Step 2: Run Gemini interactively
    run_gemini_analysis()

    # Prompt before moving to CodeRabbit
    print()
    print("=" * 60)
    input("Press Enter to continue to CodeRabbit analysis...")
    print()

    # Step 3: Run CodeRabbit interactively
    run_coderabbit_analysis()

    print()
    print("=" * 60)
    print("Analysis Complete!")
    print("=" * 60)
    print()
    print(f"📁 Results saved in: {TARGET_CODEBASE}")
    print()

    return 0


if __name__ == "__main__":
    exit(main())

