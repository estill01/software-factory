"""Render the maintained role prompts with this explicitly requested GCP backend."""
import re
from pathlib import Path


HEADINGS = {
    "liveness": "Liveness-sentinel role prompt",
    "watcher": "Watcher role prompt",
    "base_reviewer": "Semantic base-reviewer role prompt",
    "reviewer": "Reviewer role prompt",
    "fix_executor": "Supervisor fix-executor role prompt",
}


def role_prompt(config, name):
    policy = (Path(config["helper_path"]).parent.parent / "references/supervision-policy.md").read_text()
    section = policy.split("## "+HEADINGS[name]+"\n", 1)[1].split("\n## ", 1)[0]
    prompt = section.split("```text\n", 1)[1].split("\n```", 1)[0]
    cli = config["native_cli"]
    replacements = {
        "TARGET_THREAD_ID": config["target_thread_id"],
        "LOG_HELPER": cli+" helper --",
        "NOTICE_REVIEWER_THREAD_ID": "not-configured-notifications-disabled",
        "EXACT_COMPACT_STATUS": "CURRENT_OBSERVED_STATUS",
        "EXACT_COMPACT_UPDATED_AT": "CURRENT_OBSERVED_UPDATED_AT",
        "N": "N",
    }
    for role, data in config["roles"].items():
        replacements[role.upper()+"_THREAD_ID"] = data["thread_id"]
    for key, value in replacements.items():
        prompt = prompt.replace("<"+key+">", value)
    if re.search(r"<[A-Z_]+>", prompt):
        raise ValueError("unresolved role placeholder")
    return prompt + f"""

GCP BACKEND — direct operator requirement, applicable to this group

All coordination and scheduling runs on GCP. Use these exact local transport
commands as the implementation of the role's task-read, log and gated-send
operations. They are permitted transport/helper calls, including for roles
whose ordinary repository-command execution is prohibited:

python3 {cli} read --thread <exact-bound-task-id>
python3 {cli} turns --thread <exact-bound-task-id> --limit 1
python3 {cli} helper -- status --target-thread {config['target_thread_id']}
python3 {cli} helper -- <helper-subcommand-and-exact-arguments>
python3 {cli} send --recipient <bound-recipient> --purpose <maintained-purpose> --source-record <exact-record> --message <exact-action>

Use exec's structured argument handling or Python subprocess argv to preserve
message bytes; never interpolate untrusted text into a shell. The send command
runs thread-route-gate itself and refuses an unbound sender. Optional extra gate
arguments follow a literal -- after the message. Never bypass this command
with a raw Codex message call. A returned queued, uncertain, failed or denied
state is not completed delivery. Role metadata and authentic schedules are
available through `python3 {cli} status`.

The transport returns direct task data with tool outputs omitted. It does not
substitute a watcher summary. Liveness may use only `read` and the helper gate;
it must never call `turns`. The native compact status is status.type and its
exact timestamp is updatedAt; pass those fields to the helper unchanged.
Replace CURRENT_OBSERVED_STATUS and CURRENT_OBSERVED_UPDATED_AT with those
fresh observed values before calling the helper; they are not literal values.

The operator authorized these five role tasks and GCP-owned schedules. Their
real gcp-* schedule IDs belong to the runtime SQLite owner, not desktop
automation.toml files. Do not invent desktop automation state. Read the current
helper at each wake. The maintained incident, mission, routing and semantic
review rules remain controlling. Propose-only maintenance remains in force.

No Gmail or other outbound communication is authorized. No notification roles
are configured. Skip Gmail-dependent actions; retain material findings locally
and use only permitted task steering. Do not ask the user to enable Gmail or
claim a Gmail delivery/legacy terminal-shutdown receipt. Runtime pause/resume
controls affect the real GCP schedules and do not alone establish semantic
mission completion. Ordinary unchanged-state results remain quiet.

The monitored patent implementation's authority is {config['patent_tracker']}.
The current task is repairing its GCP supervision prerequisite under the user's
explicit instruction. That repair is legitimate target work. It does not
complete the patent tracker or release its separately owned R/E dependencies.
Do not reinterpret source task idleness as sufficient evidence of completion.
Do not launch subagents, replace the target, or edit its implementation.
"""
