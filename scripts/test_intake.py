#!/usr/bin/env python3
"""
Test intake form submission end-to-end.

Usage:
    doppler run -- python scripts/test_intake.py

Requires services to be running:
    - Worker on http://localhost:8787
    - Database accessible via DATABASE_URL
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

import psycopg


def main() -> int:
    print("Testing intake form submission...")
    print()

    # Generate unique test ID
    test_id = f"test-{int(time.time())}"

    # 1. Submit form to worker
    print("1. Submitting test form to worker...")

    form_data = {
        "name": f"Test User {test_id}",
        "email": f"test-{test_id}@example.com",
        "message": f"Automated test submission {test_id}",
        "source_url": "http://localhost:4321/contact",
    }

    req = urllib.request.Request(
        "http://localhost:8787/intake/coffee-shop/form",
        data=json.dumps(form_data).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ConsultTestRunner/1.0",  # Cloudflare blocks Python-urllib
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            response = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"   ✗ FAILED: Could not submit form - {e}")
        return 1

    print(f"   Response: {response}")

    submission_id = response.get("submission_id")
    if not submission_id:
        print("   ✗ FAILED: No submission_id in response")
        return 1

    print(f"   Submission ID: {submission_id}")
    print("   ✓ Form submitted")

    # 2. Verify in database
    print()
    print("2. Verifying submission in database...")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("   ✗ FAILED: DATABASE_URL not set")
        return 1

    try:
        conn = psycopg.connect(database_url)
        cur = conn.cursor()

        cur.execute(
            "SELECT id, client_slug, channel FROM inbox_submission WHERE id = %s",
            (submission_id,),
        )
        row = cur.fetchone()

        if not row:
            print("   ✗ FAILED: Submission not found in database")
            conn.close()
            return 1

        print(f"   Found: id={row[0]}, client={row[1]}, channel={row[2]}")
        print("   ✓ Database verified")

        # 3. Cleanup
        print()
        print("3. Cleaning up test data...")

        cur.execute("DELETE FROM inbox_submission WHERE id = %s", (submission_id,))
        conn.commit()
        print(f"   Deleted {cur.rowcount} row(s)")
        print("   ✓ Cleanup complete")

        conn.close()

    except psycopg.Error as e:
        print(f"   ✗ FAILED: Database error - {e}")
        return 1

    print()
    print("═══════════════════════════════════════")
    print("  INTAKE TEST PASSED")
    print("═══════════════════════════════════════")

    return 0


if __name__ == "__main__":
    sys.exit(main())
