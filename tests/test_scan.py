import os, sys, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import scan

class Scan(unittest.TestCase):
    def kinds(self, t): return [h.split(": ")[1] for h in scan.scan_text("x", t)]
    def test_email(self): self.assertEqual(self.kinds("mail me a" + "@b.com"), ["email"])
    def test_noreply_ok(self): self.assertEqual(self.kinds("1+bot@users.noreply.github.com"), [])
    def test_token(self): self.assertIn("github-token", self.kinds("t = " + "gh" + "p_" + "a" * 30))
    def test_password(self): self.assertIn("password-assign", self.kinds('password = "hunter22"'))
    def test_private_key(self): self.assertIn("private-key", self.kinds("-----BEGIN " + "RSA PRIVATE KEY-----"))
    def test_phone(self): self.assertIn("phone", self.kinds("call +1 415 555 0132"))
    def test_dates_ok(self): self.assertEqual(self.kinds("fetched 2026-11-25T14:32:23Z and 2026-11-25"), [])
    def test_action_sha_pin_ok(self): self.assertEqual(self.kinds("      - uses: actions/checkout@" + "a" * 40 + " # v4\n"), [])
    def test_bare_sha_still_flagged(self): self.assertIn("long-secret", self.kinds("key: " + "a" * 40))
    def test_sha_in_other_line_flagged(self): self.assertIn("long-secret", self.kinds("run: echo " + "a" * 40))
    def test_repo_clean(self): self.assertEqual(scan.scan(ROOT), [])
if __name__ == "__main__":
    unittest.main()
