#!/usr/bin/env python3
"""Focused tests for Block 4 bounded portfolio selection and placement."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("product_program_selection.py")
FIXTURES = SCRIPT.parents[1] / "fixtures"

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module

MODULE = load_module("product_program_selection", SCRIPT)
EVOLUTION = load_module("selection_evolution", SCRIPT.with_name("product_program_evolution.py"))
REFLECTION = load_module("selection_reflection", SCRIPT.with_name("product_program_reflection.py"))
REFLECTION_TEST = load_module("selection_reflection_test", SCRIPT.with_name("test_product_program_reflection.py"))
RESOURCES = load_module("selection_resources", SCRIPT.with_name("product_program_resources.py"))


class ProductProgramSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = json.loads((FIXTURES / "program_evidence_reflection_v1.json").read_text())
        resource_packet = json.loads((FIXTURES / "program_evidence_resource_v1.json").read_text())
        self.packet["resource_sources"] = deepcopy(resource_packet["resource_sources"])
        self.reroot_packet()
        self.inventory = json.loads((FIXTURES / "product_program_inventory_v1.json").read_text())
        reflection_submission = REFLECTION_TEST.base_submission(self.packet)
        unreviewed = REFLECTION.build_reflection(self.packet, reflection_submission, self.inventory)
        self.reflection = REFLECTION.apply_semantic_review(
            self.packet, unreviewed, self.inventory, REFLECTION_TEST.review_submission(unreviewed)
        )
        self.resource_source = json.loads((FIXTURES / "program_resource_source_v1.json").read_text())
        self.resource = RESOURCES.build_resource_evidence(self.packet, self.resource_source)
        self.submission = self.base_submission()

    def reroot_packet(self) -> None:
        self.packet["material_change_fingerprint"] = EVOLUTION.digest({"kind":"product-program-material-change","value":EVOLUTION._semantic_material_from_packet(self.packet)})
        self.packet["packet_id"] = f"program-packet-{self.packet['material_change_fingerprint'][:20]}"
        self.packet["currentness_root"] = EVOLUTION.digest({"kind":"product-program-currentness","material_change_fingerprint":self.packet["material_change_fingerprint"],"range_head":self.packet["range"]["range_head"],"repository":self.packet["repository"],"source_currentness":{"product_sources":self.packet["product_sources"],"reports":self.packet["reports"],"resource_sources":self.packet["resource_sources"]},"supervision":self.packet["supervision"],"tracker_sha256":self.packet["tracker"]["sha256"]})
        self.packet["artifact_root"] = EVOLUTION.digest({key:self.packet[key] for key in self.packet if key!="artifact_root"})

    def dimension(self, candidate_id: str, *, favorable: bool = False) -> dict[str, object]:
        values = {name:"mixed" for name in MODULE.DIMENSIONS}
        values.update({"expected_benefit":"favorable" if favorable else "mixed","coordination_cost":"favorable","protected_capability_effect":"favorable","evidence_strength":"favorable"})
        return {"candidate_id":candidate_id,"evidence_ids":["outcome-1"],"values":values}

    def lane(self, lane_id: str, candidate_id: str, *, dependencies=None, scope="scope-current-program") -> dict[str, object]:
        return {"budget":{"execution_units":3,"exploration_units":1,"review_units":1},"candidate_ids":[candidate_id],"dependency_lane_ids":dependencies or [],"evidence_ids":["outcome-1"],"expected_effect_id":"improve-operator-outcome","integration_owner":"tracker-author","lane_id":lane_id,"revisit_id":"material-outcome-change","rollback_id":"return-to-current-program","shared_resource_exclusions":[],"stop_id":"outcome-disconfirmed","writable_scopes":[scope],"writer_id":"tracker-author"}

    def base_submission(self) -> dict[str, object]:
        return {"adjudication":{"adjudicator_id":"none","decision":"not-required","evidence_ids":[],"finding_ids":[],"required":False,"tradeoff_ids":[]},"dimensions":[self.dimension("candidate-feature",favorable=True),self.dimension("candidate-no-change"),self.dimension("candidate-simplify")],"disposition":"revise-current-program","early_stop_rules":["outcome-disconfirmed","resource-ceiling-reached","stale-currentness"],"kind":"product-program-selection-submission","lanes":[self.lane("lane-current-program","candidate-feature")],"operator_ceiling":{"active_tracker_limit":2,"budget":{"execution_units":8,"exploration_units":4,"review_units":4},"concurrency_limit":2,"evidence_class":"observed","evidence_ids":["resource-a"]},"packet_root":self.packet["artifact_root"],"reflection_root":self.reflection["artifact_root"],"rejected_candidates":[{"candidate_id":"candidate-no-change","evidence_ids":["outcome-1"],"reason_id":"no-material-gain"},{"candidate_id":"candidate-simplify","evidence_ids":["outcome-1"],"reason_id":"evidence-weaker-than-selected"}],"resource_evidence_root":self.resource["artifact_root"],"schema_version":1,"scheduling_groups":[{"group_id":"group-current","lane_ids":["lane-current-program"],"mode":"sequential"}],"selected_candidate_ids":["candidate-feature"],"selector_id":"portfolio-selector"}

    def build(self, submission=None):
        return MODULE.build_artifacts(self.packet,self.inventory,self.reflection,self.resource_source,self.resource,submission or self.submission)

    def reject(self, submission, pattern):
        with self.assertRaisesRegex(MODULE.ProductProgramError,pattern): self.build(submission)

    def test_deterministic_selection_portfolio_and_handoff_are_nonauthorizing(self):
        first=self.build(); second=self.build(deepcopy(self.submission)); self.assertEqual(MODULE.canonical(first),MODULE.canonical(second))
        self.assertTrue(MODULE.verify_artifacts(self.packet,self.inventory,self.reflection,self.resource_source,self.resource,first)["verified"])
        self.assertEqual("current-program-author",first["handoff"]["placement"]); self.assertEqual("tracker-author",first["handoff"]["owner"])
        self.assertFalse(first["selection"]["authority"]["application_allowed"])
        self.assertEqual([0,1],first["handoff"]["preconditions"]["requested_blocks"])

    def test_exact_reuse_is_zero_work(self):
        bundle=self.build(); verified=MODULE.verify_artifacts(self.packet,self.inventory,self.reflection,self.resource_source,self.resource,bundle)
        self.assertTrue(verified["verified"])

    def test_committed_bundle_verifies(self):
        bundle=json.loads((FIXTURES/"program_selection_bundle_v1.json").read_text())
        self.assertTrue(MODULE.verify_artifacts(self.packet,self.inventory,self.reflection,self.resource_source,self.resource,bundle)["verified"])

    def test_cli_build_verify_and_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); values={"packet":self.packet,"inventory":self.inventory,"reflection":self.reflection,"resource-source":self.resource_source,"resource-evidence":self.resource,"submission":self.submission}
            paths={}
            for name,value in values.items():
                path=root/f"{name}.json"; path.write_bytes(MODULE.canonical(value)); paths[name]=path
            common=[sys.executable,str(SCRIPT),"build","--packet",str(paths["packet"]),"--inventory",str(paths["inventory"]),"--reflection",str(paths["reflection"]),"--resource-source",str(paths["resource-source"]),"--resource-evidence",str(paths["resource-evidence"]),"--submission",str(paths["submission"])]
            built=json.loads(subprocess.run(common,check=True,capture_output=True).stdout); bundle=root/"bundle.json"; bundle.write_bytes(MODULE.canonical(built["bundle"]))
            base=["--packet",str(paths["packet"]),"--inventory",str(paths["inventory"]),"--reflection",str(paths["reflection"]),"--resource-source",str(paths["resource-source"]),"--resource-evidence",str(paths["resource-evidence"]),"--bundle",str(bundle)]
            verified=json.loads(subprocess.run([sys.executable,str(SCRIPT),"verify",*base],check=True,capture_output=True).stdout); self.assertTrue(verified["verified"])
            reused=json.loads(subprocess.run([sys.executable,str(SCRIPT),"reuse",*base],check=True,capture_output=True).stdout); self.assertEqual(0,reused["model_calls"]); self.assertFalse(reused["cognitive_work_started"])

    def test_candidate_coverage_and_self_selection_reject(self):
        missing=deepcopy(self.submission); missing["dimensions"].pop(); self.reject(missing,"compare every candidate")
        collapsed=deepcopy(self.submission); collapsed["selector_id"]="reflection-generator"; self.reject(collapsed,"selector conflicts")

    def test_budget_capacity_and_current_range_are_bounded(self):
        over=deepcopy(self.submission); over["lanes"][0]["budget"]["execution_units"]=9; self.reject(over,"exceeds the current operator ceiling")
        estimated=deepcopy(self.submission); estimated["operator_ceiling"]["evidence_class"]="estimated"; self.reject(estimated,"must not be presented")
        bundle=self.build(); forged=deepcopy(bundle); forged["handoff"]["preconditions"]["requested_blocks"]=[0]
        forged["handoff"]["handoff_root"]=MODULE.digest({key:forged["handoff"][key] for key in forged["handoff"] if key!="handoff_root"})
        with self.assertRaises(MODULE.ProductProgramError): MODULE.verify_artifacts(self.packet,self.inventory,self.reflection,self.resource_source,self.resource,forged)

    def test_cycle_and_dependent_parallelism_reject(self):
        multi=self.multi_submission(); multi["lanes"][0]["dependency_lane_ids"]=["lane-simplify"]; multi["lanes"][1]["dependency_lane_ids"]=["lane-feature"]; self.reject(multi,"cyclic")
        parallel=self.multi_submission(); parallel["lanes"][1]["dependency_lane_ids"]=["lane-feature"]; parallel["scheduling_groups"][0]["mode"]="parallel"; self.reject(parallel,"dependent lanes")

    def multi_submission(self):
        result=deepcopy(self.submission); result["disposition"]="start-program-portfolio"; result["selected_candidate_ids"]=["candidate-feature","candidate-simplify"]
        result["rejected_candidates"]=[{"candidate_id":"candidate-no-change","evidence_ids":["outcome-1"],"reason_id":"no-material-gain"}]
        for item in result["dimensions"]:
            if item["candidate_id"]=="candidate-simplify": item["values"]["expected_benefit"]="favorable"
        result["lanes"]=[self.lane("lane-feature","candidate-feature",scope="scope-a"),self.lane("lane-simplify","candidate-simplify",scope="scope-b")]
        result["scheduling_groups"]=[{"group_id":"group-portfolio","lane_ids":["lane-feature","lane-simplify"],"mode":"parallel"}]
        return result

    def test_parallel_writers_overlap_and_missing_integration_reject(self):
        overlap=self.multi_submission(); overlap["lanes"][1]["writable_scopes"]=["scope-a"]; overlap["lanes"][0]["integration_owner"]="none"; overlap["lanes"][1]["integration_owner"]="none"; self.reject(overlap,"overlapping writers")

    def test_portfolio_disposition_and_candidate_lane_ownership_are_exact(self):
        single=deepcopy(self.submission); single["disposition"]="start-program-portfolio"; self.reject(single,"requires multiple justified lanes")
        duplicate=self.multi_submission(); duplicate["lanes"][1]["candidate_ids"]=["candidate-feature","candidate-simplify"]; self.reject(duplicate,"repeat IDs or omit selected candidates")

    def test_capacity_class_and_adjudication_evidence_are_bound(self):
        mismatch=deepcopy(self.submission); mismatch["operator_ceiling"]["evidence_ids"]=["resource-b-estimate"]; self.reject(mismatch,"class differs from retained resource evidence")
        unsupported=deepcopy(self.submission); unsupported["adjudication"]={"adjudicator_id":"independent-max","decision":"accepted","evidence_ids":["outcome-1"],"finding_ids":[],"required":True,"tradeoff_ids":["tradeoff-placement"]}; self.reject(unsupported,"not independently accepted")

    def test_selected_benefit_must_exceed_coordination_cost(self):
        weak=deepcopy(self.submission); weak["dimensions"][0]["values"]["expected_benefit"]="mixed"; self.reject(weak,"benefit does not exceed")
        costly=deepcopy(self.submission); costly["dimensions"][0]["values"]["coordination_cost"]="adverse"; self.reject(costly,"benefit does not exceed")

    def test_consequential_unresolved_tradeoff_requires_independent_adjudication(self):
        missing=deepcopy(self.submission); missing["adjudication"]={"adjudicator_id":"independent-max","decision":"rejected","evidence_ids":["report-1"],"finding_ids":["finding-1"],"required":True,"tradeoff_ids":["tradeoff-placement"]}; self.reject(missing,"not independently accepted")
        accepted=deepcopy(self.submission); accepted["adjudication"]={"adjudicator_id":"independent-max","decision":"accepted","evidence_ids":["report-1"],"finding_ids":[],"required":True,"tradeoff_ids":["tradeoff-placement"]}; self.assertTrue(self.build(accepted)["selection"]["rationale"]["adjudication"]["required"])

    def test_unchanged_disposition_emits_no_lane_and_fixed_placement(self):
        unchanged=deepcopy(self.submission); unchanged["disposition"]="continue-program-unchanged"; unchanged["selected_candidate_ids"]=["candidate-no-change"]; unchanged["lanes"]=[]; unchanged["scheduling_groups"]=[]
        unchanged["rejected_candidates"]=[{"candidate_id":"candidate-feature","evidence_ids":["outcome-1"],"reason_id":"no-material-gain"},{"candidate_id":"candidate-simplify","evidence_ids":["outcome-1"],"reason_id":"no-material-gain"}]
        bundle=self.build(unchanged); self.assertEqual("none",bundle["handoff"]["placement"]); self.assertEqual("none",bundle["handoff"]["owner"])

    def test_stale_roots_and_artifact_tampering_reject(self):
        stale=deepcopy(self.submission); stale["resource_evidence_root"]="0"*64; self.reject(stale,"stale")
        bundle=self.build(); bundle["portfolio"]["aggregate_budget"]["execution_units"]+=1
        with self.assertRaises(MODULE.ProductProgramError): MODULE.verify_artifacts(self.packet,self.inventory,self.reflection,self.resource_source,self.resource,bundle)


if __name__ == "__main__": unittest.main()
