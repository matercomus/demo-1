import os
import sys
import json
import argparse
from typing import List, Dict, Any
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.agents.stage_classifier import classify_stage_llm

PROMPT_PATH = os.path.join(os.path.dirname(__file__), '../prompts/stage_classifier_prompt.md')
TEST_CASES_PATH = os.path.join(os.path.dirname(__file__), 'stage_classifier_test_cases.json')
RESULTS_PATH = os.path.join(os.path.dirname(__file__), 'stage_classifier_test_results.json')


def load_prompt() -> str:
    with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def save_prompt(new_prompt: str):
    with open(PROMPT_PATH, 'w', encoding='utf-8') as f:
        f.write(new_prompt)

def load_test_cases(extra_examples_path: str = None) -> List[Dict[str, Any]]:
    with open(TEST_CASES_PATH, 'r', encoding='utf-8') as f:
        base_cases = json.load(f)
    if extra_examples_path:
        with open(extra_examples_path, 'r', encoding='utf-8') as f:
            extra_cases = json.load(f)
        # Merge, avoiding duplicates by reply+expected_stage
        seen = set()
        all_cases = []
        for c in base_cases + extra_cases:
            key = (c['reply'], c['expected_stage'])
            if key not in seen:
                all_cases.append(c)
                seen.add(key)
        return all_cases
    return base_cases

def run_test_case(reply: str, expected_stage: str) -> Dict[str, Any]:
    got_stage = classify_stage_llm(reply)
    return {
        'reply': reply,
        'expected_stage': expected_stage,
        'got_stage': got_stage,
        'ok': got_stage == expected_stage
    }

def suggest_prompt(prompt: str, failed: List[Dict[str, Any]]) -> str:
    from openai import OpenAI
    client = OpenAI()
    suggestion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert prompt engineer. Given a prompt and failed test cases, suggest how to improve the prompt to fix the failures. Only output improved prompt text, nothing else."},
            {"role": "user", "content": f"Current prompt:\n\n{prompt}\n\nFailures:\n" + '\n'.join([f"Reply: {f['reply']}\nExpected: {f['expected_stage']}\nGot: {f['got_stage']}" for f in failed])}
        ],
        max_tokens=1024,
        temperature=0.2
    )
    return suggestion.choices[0].message.content.strip()

def run_tests(verbose=True, extra_examples_path=None):
    prompt = load_prompt()
    test_cases = load_test_cases(extra_examples_path)
    results = []
    for i, case in enumerate(test_cases):
        reply = case['reply']
        expected_stage = case['expected_stage']
        result = run_test_case(reply, expected_stage)
        result['description'] = case.get('description', f"Case {i+1}")
        results.append(result)
        if verbose:
            print(f"[{i+1}] {result['description']}\n  Expected: {expected_stage}\n  Got:      {result['got_stage']}  {'✅' if result['ok'] else '❌'}\n  Reply:    {reply[:80]}{'...' if len(reply) > 80 else ''}\n")
    with open(RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    failed = [r for r in results if not r['ok']]
    return results, failed

def main():
    parser = argparse.ArgumentParser(description="Stage classifier prompt tester and auto-tuner.")
    parser.add_argument('--auto', action='store_true', help='Enable auto-tune mode (edit prompt and rerun until all pass or max trials)')
    parser.add_argument('--max-trials', type=int, default=10, help='Max auto-tune trials (default: 10)')
    parser.add_argument('--no-verbose', action='store_true', help='Suppress per-case output')
    parser.add_argument('--examples', type=str, default=None, help='Path to extra examples JSON file to augment test cases (e.g. tools/stage_classifier_examples.json)')
    args = parser.parse_args()

    trial = 1
    all_passed = False
    history = []
    while trial <= args.max_trials:
        print(f"\n=== Trial {trial} ===\n")
        results, failed = run_tests(verbose=not args.no_verbose, extra_examples_path=args.examples)
        n_failed = len(failed)
        n_total = len(results)
        print(f"\nSummary: {n_total-n_failed}/{n_total} passed, {n_failed} failed.")
        history.append({'trial': trial, 'n_failed': n_failed})
        if n_failed == 0:
            all_passed = True
            print("\nAll test cases passed! 🎉")
            break
        if not args.auto:
            print(f"\n{n_failed} failures. Suggesting prompt tweaks...\n")
            try:
                improved_prompt = suggest_prompt(load_prompt(), failed)
                print("\n--- Improved Prompt Suggestion ---\n")
                print(improved_prompt)
                print("\n--- End Suggestion ---\n")
            except Exception as e:
                print(f"Could not get LLM suggestion: {e}")
            break
        else:
            print(f"\n{n_failed} failures. Auto-tuning prompt (trial {trial})...\n")
            try:
                improved_prompt = suggest_prompt(load_prompt(), failed)
                save_prompt(improved_prompt)
                print(f"Prompt updated. Re-running tests...")
                time.sleep(1)  # Small delay to avoid rate limits
            except Exception as e:
                print(f"Could not auto-tune prompt: {e}")
                break
        trial += 1
    if not all_passed:
        print(f"\nAuto-tune stopped after {trial-1} trials. Some tests still failing.")
    print("\nAuto-tune history:")
    for h in history:
        print(f"  Trial {h['trial']}: {h['n_failed']} failures")

if __name__ == '__main__':
    main() 