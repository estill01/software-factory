"""Exact semantic authority may differ from the descriptive mission source."""
import base64
import copy
import hashlib
import unittest
from pathlib import Path
from unittest import mock

import test_supervision_log as support

owner = support.supervision_log
SOURCE = "and ultimately I don't care how you achieve this -- I want to be able to run `supervise tracker runs` and have it work no matter if it's on my laptop or on the GCP system. if you need to build scripts or other things to get it to work then do that.\u00a0\n"


class DirectRangeSourceTests(unittest.TestCase):
    def setUp(self):
        self.case = support.ImplementationRangeControlTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.public_key.chmod(0o600)
        self.call = self.case.call
        self.target = self.case.target
        self.directory = self.case.root / self.target
        self.policy = owner.read_json(self.directory / "policy.json")
        self.mission = copy.deepcopy(self.policy["mission_binding"])
        self.item = "01a0726f-31b9-7e80-b46d-ff58184beb50"
        self.turn = "01a0726d-3ff7-73b3-8947-2358e5311615"
        self.record = f"direct-user:{self.target}:{self.item}"
        self.sha = hashlib.sha256(SOURCE.encode()).hexdigest()
        self.encoded = base64.b64encode(SOURCE.encode()).decode()
        self.case.write_tracker(["completed"] * 3)

    def review(self, classification="full-tracker", mission=None, reviewer=None, extra=()):
        evidence = [
            f"source-kind:{owner.DIRECT_AUTHORITY_SOURCE_KIND}",
            f"source-task:{self.target}", f"source-turn:{self.turn}",
            f"source-item:{self.item}", f"source-record:{self.record}",
            "source-byte-count:251", f"source-sha256:{self.sha}",
            f"verifier:{reviewer or self.case.reviewer}",
            f"classification:{classification}", "review-findings:none",
            f"mission-root:{mission or self.mission['mission_root']}",
            *extra,
        ]
        self.call(
            "record", "--target-thread", self.target, "--kind", "meta-review",
            "--active-block", "2", "--checkpoint", "direct-source-review",
            "--status", "accepted", "--severity", "info",
            "--summary", "Independent exact direct source semantic review",
            "--category", owner.DIRECT_AUTHORITY_REVIEW_CATEGORY,
            "--model", "gpt-5.6-sol", "--reasoning", "max",
            "--resolution-owner", "supervisor", "--user-action-required", "no",
            *(argument for value in evidence for argument in ("--evidence", value)),
        )
        return owner.events(self.directory / "events.jsonl")[-1]["record_id"]

    def sign_args(self, review):
        return [
            "implementation-range-authority-source-review-sign",
            "--target-thread", self.target, "--source-task", self.target,
            "--source-turn", self.turn, "--source-item", self.item,
            "--source-record", self.record, "--source-text-base64", self.encoded,
            "--review-evidence-record", review,
            "--expected-policy-sha256", self.policy["policy_sha256"],
        ]

    def ingest_args(self, path):
        return [
            "implementation-range-authority-source-ingest",
            "--target-thread", self.target, "--source-task", self.target,
            "--source-item", self.item, "--source-record", self.record,
            "--source-text-base64", self.encoded,
            "--provenance-review-record", str(path),
            "--expected-policy-sha256", self.policy["policy_sha256"],
        ]

    def state(self):
        return {name: (self.directory / name).read_bytes() for name in (
            "policy.json", "policy-history.jsonl", "events.jsonl",
            owner.EVENT_LEDGER_ANCHOR_NAME,
        )}

    def signed(self):
        return self.call(*self.sign_args(self.review()))["output_json"]

    def ingest_and_receipt(self, path):
        event = self.call(*self.ingest_args(path))["record"]
        self.call("implementation-range-authority-receipt", "--target-thread",
                  self.target, "--authority-event-record", event["record_id"])
        return event

    def retained(self, policy=None, all_events=None):
        return owner.retained_full_tracker_authority(
            policy or owner.read_json(self.directory / "policy.json"),
            all_events=all_events or owner.events(self.directory / "events.jsonl"),
            policy_history=owner.events(self.directory / "policy-history.jsonl"),
            source_record=self.record, source_sha256=self.sha,
            require_current_receipt=True, request_text=SOURCE,
        )

    def test_exact_source_binds_full_tracker_without_relabeling_mission(self):
        self.assertEqual(len(SOURCE.encode()), 251)
        self.assertEqual(self.sha, "792e2627e071a097a3807a9d928d2821dd23dd4438f8d37f6d6b9be043fd22ec")
        with self.assertRaises(owner.SupervisionLogError):
            owner.classify_implementation_request(SOURCE, {0, 1, 2})
        event = self.ingest_and_receipt(self.signed())
        self.assertEqual(event["source_sha256"], self.sha)
        self.retained()
        bound = self.call(
            "implementation-range-bind", "--target-thread", self.target,
            "--range-id", "RANGE-DESCRIPTIVE-EXACT", "--tracker", str(self.case.tracker),
            "--request-text-base64", self.encoded,
            "--authority-source-record", self.record,
            "--authority-source-sha256", self.sha,
        )
        self.assertEqual(bound["binding"]["range_intent"], "full-tracker")
        policy = owner.read_json(self.directory / "policy.json")
        self.assertEqual(policy["mission_binding"], self.mission)
        self.assertNotEqual(policy["policy_sha256"], self.policy["policy_sha256"])
        gate = self.call("implementation-range-gate", "--target-thread", self.target,
                         "--response-kind", "outcome-terminal")
        self.assertTrue(gate["range_binding_current"])
        self.assertEqual(gate["remaining_blocks"], [])

    def test_sign_rejects_wrong_source_or_stale_policy_before_key_access(self):
        args = self.sign_args(self.review())
        before = self.state()
        cases = [("--source-task", "wrong-target-1234"),
                 ("--source-item", "wrong-item-1234"),
                 ("--source-record", "wrong-record-1234"),
                 ("--source-turn", "wrong-turn-1234"),
                 ("--source-text-base64", base64.b64encode(SOURCE.rstrip().encode()).decode()),
                 ("--expected-policy-sha256", "f" * 64),
                 ("--review-evidence-record", "EVT-999999")]
        with mock.patch.object(owner, "trusted_adaptive_reviewer_private_key",
                               side_effect=AssertionError("key accessed")):
            for flag, value in cases:
                changed = args.copy()
                changed[changed.index(flag) + 1] = value
                with self.subTest(flag=flag), self.assertRaises(owner.SupervisionLogError):
                    self.call(*changed)
                self.assertEqual(self.state(), before)

    def test_sign_requires_full_tracker_current_mission_and_bound_reviewer(self):
        for options in ({"classification": "explicit-blocks"},
                        {"mission": "f" * 64}, {"reviewer": self.target}):
            review = self.review(**options)
            before = self.state()
            with self.subTest(options=options), self.assertRaises(owner.SupervisionLogError):
                self.call(*self.sign_args(review))
            self.assertEqual(self.state(), before)

    def test_ingest_rejects_wrong_target_bytes_policy_and_signature(self):
        path = self.signed()
        payload = owner.read_json(Path(path))
        payload["source_sha256"] = "f" * 64
        bad = self.case.root / "tampered-source-review.json"
        bad.write_bytes(owner.canonical(payload))
        args = self.ingest_args(path)
        before = self.state()
        for flag, value in (("--source-task", "wrong-target-1234"),
                            ("--source-text-base64", base64.b64encode((SOURCE + "!").encode()).decode()),
                            ("--expected-policy-sha256", "f" * 64),
                            ("--provenance-review-record", str(bad))):
            changed = args.copy()
            changed[changed.index(flag) + 1] = value
            with self.subTest(flag=flag), self.assertRaises(owner.SupervisionLogError):
                self.call(*changed)
            self.assertEqual(self.state(), before)

    def test_conflicting_review_tokens_are_not_clean(self):
        for token in ("review-findings:critical", "source-task:wrong-target-1234",
                      "source-sha256:" + "f" * 64, "mission-root:" + "f" * 64):
            review = self.review(extra=[token])
            before = self.state()
            with self.subTest(token=token), self.assertRaises(owner.SupervisionLogError):
                self.call(*self.sign_args(review))
            self.assertEqual(self.state(), before)

    def test_later_ambiguous_findings_invalidates_replay(self):
        self.ingest_and_receipt(self.signed())
        self.review(extra=["review-findings:critical"])
        with self.assertRaises(owner.SupervisionLogError):
            self.retained()

    def test_later_non_full_tracker_review_invalidates_replay(self):
        path = self.signed()
        self.ingest_and_receipt(path)
        self.review(classification="explicit-blocks")
        args = self.ingest_args(path)
        args[-1] = owner.read_json(self.directory / "policy.json")["policy_sha256"]
        before = self.state()
        with self.assertRaises(owner.SupervisionLogError):
            self.call(*args)
        with self.assertRaises(owner.SupervisionLogError):
            self.retained()
        self.assertEqual(self.state(), before)

    def test_wrong_mission_and_unsigned_event_cannot_replay(self):
        event = self.ingest_and_receipt(self.signed())
        policy = owner.read_json(self.directory / "policy.json")
        changed = copy.deepcopy(policy)
        changed["mission_binding"] = owner.mission_binding_contract("f" * 64, "other-mission-1234")
        with self.assertRaises(owner.SupervisionLogError):
            self.retained(policy=changed)
        unsigned = {key: event[key] for key in owner.DIRECT_AUTHORITY_EVENT_FIELDS}
        all_events = [unsigned if item["record_id"] == event["record_id"] else item
                      for item in owner.events(self.directory / "events.jsonl")]
        with self.assertRaisesRegex(owner.SupervisionLogError, "requires signed"):
            owner.canonical_direct_authority_event(
                all_events, event_record_id=event["record_id"], policy=policy,
                policy_history=owner.events(self.directory / "policy-history.jsonl"),
            )

    def test_duplicate_ingestion_cannot_cross_missions(self):
        self.case.bind()
        self.policy = owner.read_json(self.directory / "policy.json")
        path = self.signed()
        self.ingest_and_receipt(path)
        self.case.complete_predecessor_and_start_successor(
            retain_range_authority=False, mission_source_record=self.record,
            mission_source_sha256=self.sha,
        )
        args = self.ingest_args(path)
        args[-1] = owner.read_json(self.directory / "policy.json")["policy_sha256"]
        before = self.state()
        with self.assertRaises(owner.SupervisionLogError):
            self.call(*args)
        self.assertEqual(self.state(), before)


if __name__ == "__main__":
    unittest.main()
