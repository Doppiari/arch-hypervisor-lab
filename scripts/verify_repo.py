#!/usr/bin/env python3
from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
errors: list[str] = []

def fail(message: str) -> None:
    errors.append(message)

# Relative Markdown links.
link_re = re.compile(r"\[[^]]*\]\(([^)]+)\)")
for doc in root.rglob("*.md"):
    if ".git" in doc.parts:
        continue
    for target in link_re.findall(doc.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path = (doc.parent / target.split("#", 1)[0]).resolve()
        if not path.exists():
            fail(f"broken link: {doc.relative_to(root)} -> {target}")

compat = yaml.safe_load((root / "hardware/compatibility.yml").read_text())
expected = {"nitro-3060", "predator-3070"}
if set(compat["systems"]) != expected:
    fail("compatibility matrix must contain both target laptops")
for name, system in compat["systems"].items():
    if len(system["vfio_ids"]) != 2:
        fail(f"{name}: expected GPU and HDMI-audio PCI IDs")
    if system["components"].get("full_pipeline") not in {"pipeline-pending", "pipeline-verified"}:
        fail(f"{name}: invalid full_pipeline state")

network_doc = (root / "configs/network-domains.md").read_text()
for name in ("clean", "dirty", "dev", "lab", "services"):
    if name not in network_doc:
        fail(f"network document missing {name}")

lg_xml = (root / "configs/libvirt/looking-glass.xml").read_text()
if not re.search(
    r"<graphics\s+type=['\"]spice['\"][^>]*>\s*"
    r"<listen\s+type=['\"]socket['\"]\s+"
    r"socket=['\"]/run/hyperlab-spice/DOMAIN\.sock['\"]\s*/>\s*"
    r"</graphics>",
    lg_xml,
    re.DOTALL,
):
    fail("Looking Glass VFIO SPICE example must use the reviewed per-domain Unix socket")
if "size':67108864" not in lg_xml:
    fail("Looking Glass VFIO example must use the reviewed 64 MiB kvmfr region")
if re.search(r"<graphics\s+type=['\"]spice['\"][^>]*port=['\"]5900['\"]", lg_xml):
    fail("Looking Glass VFIO example must not restore TCP port authority")

for entry in (root / "configs/boot").glob("*.conf"):
    text = entry.read_text()
    if "cryptdevice=" in text:
        fail(f"legacy encrypt syntax in {entry.name}")
    if re.search(r"\\\s*$", text, re.MULTILINE):
        fail(f"backslash continuation in {entry.name}")

readme = (root / "README.md").read_text(encoding="utf-8")
setup = (root / "SETUP.md").read_text(encoding="utf-8")
canonical_lg_build = "B7-263-g0140a3f6fb"

for relative in ("SETUP.md", "configs/looking-glass.md"):
    text = (root / relative).read_text(encoding="utf-8")
    for line_number, line in enumerate(text.splitlines(), start=1):
        command = line.strip()
        if command.startswith("ansible-playbook ") and not command.startswith(
            "ansible-playbook -K "
        ):
            fail(
                f"{relative}:{line_number}: ansible-playbook command must use -K"
            )

if "./verify.sh" not in setup:
    fail("SETUP must verify the stage-2 checkout before host changes")
if "The Nitro\nbootstrap-to-stage-2 host path has been reproduced" not in readme:
    fail("README must record the verified Nitro host path without promoting it")
if "the normal laptop target adds Sway and the Looking Glass host transport" not in readme:
    fail("README must describe Sway and Looking Glass as part of the normal laptop target")
# Read the operator sequence as argv, rather than recognizing a prose promise.
host_sections = re.findall(r"^### 2c\..*?\n(.*?)(?=^## )", setup, re.MULTILINE | re.DOTALL)
host_commands: list[list[str]] = []
if len(host_sections) != 1:
    fail("SETUP step 2c: expected one host sequence section")
else:
    for block in re.findall(r"^```bash\n(.*?)^```", host_sections[0], re.MULTILINE | re.DOTALL):
        for line in block.replace("\\\n", " ").splitlines():
            try:
                argv = shlex.split(line)
            except ValueError as exc:
                fail(f"SETUP step 2c: invalid shell command: {exc}")
                continue
            if argv and argv[0] == "ansible-playbook":
                host_commands.append(argv)
host_argv = ["ansible-playbook", "-K", "playbooks/v1-host.yml"]
identity_argv = ["-e", "@$LAB_VARS"]
if host_commands != [
    ["ansible-playbook", "-K", "playbooks/preflight.yml", *identity_argv],
    [*host_argv, "--check", "--diff", *identity_argv],
    [*host_argv, *identity_argv],
    [*host_argv, *identity_argv],
]:
    fail("SETUP step 2c: preflight and v1-host check/diff/two applies must retain -K and local identity")

# These visible records distinguish implemented software from qualification.
# Keep evidence attached to each state so a status cannot silently move to a
# different source. No sibling checkout is needed to check the published guide.
ansible_source = "https://github.com/importriri/hyperlab-ansible/blob/main/"
bootstrap_source = "https://github.com/importriri/arch-bootstrap/blob/main/"
host_evidence = ansible_source + "playbooks/v1-host.yml"
iso_evidence = bootstrap_source + "iso/README.md"
lease_evidence = ansible_source + "docs/adr/0019-gpu-lease.md"
campaign_evidence = ansible_source + "docs/release-evidence.md"
boundary_contract = {
    "v1 host composition": ({"lab.yml", "host-desktop-hyprland.yml", "host-sleep-guard.yml"}, host_evidence),
    "Desktop staging": ({"no Ly default", "no compositor start", "no login proof"}, host_evidence),
    "Installer ISO": ({"development-only", "unsigned", "signing-ineligible"}, iso_evidence),
    "ISO comparison": ({"two builds", "matching manifests", "unequal image bytes", "mismatch diagnosed"}, iso_evidence),
    "ISO distribution": ({"no admitted payload", "no public download"}, iso_evidence),
    "GPU lease design": ({"accepted", "workstation-dev-standard only", "default without dedicated GPU"}, lease_evidence),
    "GPU lease controls": ({"not built"}, lease_evidence),
    "Lease prerequisites": ({"image pending", "Create pending", "physical transition pending"}, lease_evidence),
    "v1 acceptance": ({"v3 prepared", "qualification pending"}, campaign_evidence),
    "v2 acceptance": ({"historical"}, campaign_evidence),
    "Nitro full pipeline": ({"pipeline-pending"}, "hardware/compatibility.yml"),
    "Predator full pipeline": ({"pipeline-pending"}, "hardware/compatibility.yml"),
}
boundary_sections = re.findall(
    r"^## Current software boundaries\n(.*?)(?=^## )", setup, re.MULTILINE | re.DOTALL
)
boundary_rows: dict[str, tuple[set[str], str]] = {}
if len(boundary_sections) != 1:
    fail("SETUP boundaries: expected one status section")
else:
    for line in boundary_sections[0].splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells == ["Item", "Current state", "Evidence"] or all(
            re.fullmatch(r":?-+:?", cell) for cell in cells
        ):
            continue
        if len(cells) != 3:
            fail("SETUP boundaries: expected three table cells")
            continue
        item, state, evidence = cells
        states = [part.strip().strip("`") for part in state.split(";")]
        links = link_re.findall(evidence)
        if item in boundary_rows or len(states) != len(set(states)) or len(links) != 1:
            fail(f"SETUP boundaries: duplicate or ambiguous record for {item}")
            continue
        boundary_rows[item] = (set(states), links[0])
if boundary_rows.keys() != boundary_contract.keys():
    fail("SETUP boundaries: missing, duplicate or unknown status records")
for item, expected_record in boundary_contract.items():
    if boundary_rows.get(item) != expected_record:
        fail(f"SETUP boundaries: {item} status/evidence mismatch")
for label, profile in (("Nitro", "nitro-3060"), ("Predator", "predator-3070")):
    item = f"{label} full pipeline"
    if boundary_rows.get(item) != (
        {compat["systems"][profile]["components"]["full_pipeline"]},
        "hardware/compatibility.yml",
    ):
        fail(f"SETUP boundaries: {item} must match compatibility matrix")

for relative, required_sources in (
    ("README.md", {host_evidence, iso_evidence, lease_evidence, campaign_evidence}),
    ("FAQ.md", {host_evidence, iso_evidence, lease_evidence, campaign_evidence}),
    ("TROUBLESHOOTING.md", {host_evidence, campaign_evidence}),
):
    targets = set(link_re.findall((root / relative).read_text(encoding="utf-8")))
    if not required_sources <= targets:
        fail(f"{relative}: missing current host/status evidence links")
# Status records cannot make contradictory newcomer prose safe. Reject the
# retired claims across every guide page, including wrapped/emphasized text.
for relative in ("README.md", "SETUP.md", "FAQ.md", "TROUBLESHOOTING.md"):
    text = (root / relative).read_text(encoding="utf-8")
    prose = re.sub(r"\s+", " ", text.replace("*", "").replace("`", "")).casefold()
    for stale in (
        "host remains headless by default",
        "Add the optional cockpit",
        "from `pending` to `verified`",
        "no profile, build, image",
        "not built or available",
        "Proposed and unimplemented",
        "lease is still Proposed",
        "integrated host entrypoint",
        "Do not guess a playbook name",
        "does **not** assemble",
        "The controls are built",
        "signed and publicly downloadable",
        "eligible for signing",
        "signing-eligible",
    ):
        claim = stale.replace("*", "").replace("`", "").casefold()
        if re.search(rf"\b{re.escape(claim)}\b", prose):
            fail(f"{relative}: stale pipeline topology claim: {stale}")
for heading in (
    "## 4. Prepare and seal images",
    "## 5. Exercise explicit VM lifecycle",
    "## 8. Register services before creation",
):
    if heading not in setup:
        fail(f"SETUP missing current stage-2 boundary: {heading}")
for relative in (
    "configs/virtual-display-windows.md",
    "problems/geforce-passthrough-needs-a-display.md",
    "problems/looking-glass-shows-spice-and-calls-it-success.md",
):
    text = (root / relative).read_text(encoding="utf-8")
    if canonical_lg_build not in text:
        fail(f"{relative}: Looking Glass build identity drift")
if "sanitized Predator examples" not in (root / "configs/boot/boot-profiles.md").read_text(encoding="utf-8"):
    fail("boot profile guide must identify checked-in PCI IDs as examples")
for placeholder in root.rglob(".gitkeep"):
    if ".git" not in placeholder.parts:
        fail(f"dead placeholder file remains tracked: {placeholder.relative_to(root)}")

if errors:
    print("REPOSITORY VERIFICATION FAILED", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)
print("repository verification: OK")
