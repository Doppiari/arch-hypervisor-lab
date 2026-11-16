# Arch Linux Hypervisor Lab

Architecture, hardware evidence and failure writeups for a laptop KVM/VFIO lab
on Arch Linux.

The project is split so installation, configuration and evidence do not certify
one another:

```text
arch-bootstrap  ->  hyperlab-ansible  ->  arch-hypervisor-lab
base system         host + workloads      evidence + writeups
```

Start with [`SETUP.md`](SETUP.md), the canonical newcomer guide from an
authenticated upstream Arch Linux live prompt through installation, the first
account and the existing host target. Use [Troubleshooting](TROUBLESHOOTING.md)
for symptoms and [FAQ](FAQ.md) for hardware, media, erasure and security limits.
The complete v1 installation remains blocked on software and hardware gates;
the guide marks the stops. The project ISO has a
[development-only result](https://github.com/importriri/arch-bootstrap/blob/main/iso/README.md):
two builds, matching package manifests but unequal image bytes with a diagnosed
mismatch. It remains unsigned and signing-ineligible, with no admitted payload
or public download. The authenticated upstream medium remains the usable route.

## Lab shape

```text
Arch Linux host
|
|-- clean     10.10.1.0/24  NAT       trusted accounts and games
|-- dirty     10.10.2.0/24  NAT       untrusted software and mods
|-- dev       10.10.3.0/24  NAT       development and 3D work
|-- lab       10.10.4.0/24  ISOLATED  controlled research
`-- services  10.10.5.0/24  NAT       private service VMs

NVIDIA dGPU -- VFIO --> one workload VM at a time
```

The existing [v1 host target](https://github.com/importriri/hyperlab-ansible/blob/main/playbooks/v1-host.yml)
composes `lab.yml` (foundation, Sway and Looking Glass), managed Hyprland/Quickshell
session staging and the VFIO sleep guard. The iGPU keeps the host usable while
the dGPU belongs to one running VFIO workload. Hyprland is preferred and Sway
remains the recovery compositor. Staging selects no Ly default, starts no
compositor and proves no login; session and Create acceptance remain separate.
Services may use the
GPU through an explicitly reviewed handoff profile and matching Template/spec.
The clean → dev → dirty → lab GPU ladder only lowers within a host boot;
returning to a cleaner use requires a host reboot. The optional per-run GPU
lease has an [Accepted design](https://github.com/importriri/hyperlab-ansible/blob/main/docs/adr/0019-gpu-lease.md)
but is not built: initially `workstation-dev-standard` only, default without the
dedicated GPU, after image readiness, Create acceptance and real transition
prerequisites. Existing VFIO Machines still start with the GPU. See the
[setup boundaries](SETUP.md#2c-reconcile-the-existing-laptop-target-stop-before-claiming-v1).

## Repository set

1. [`arch-bootstrap`](https://github.com/importriri/arch-bootstrap) installs the
   encrypted Arch base and writes the storage hand-off contract.
2. [`hyperlab-ansible`](https://github.com/importriri/hyperlab-ansible) configures
   KVM, VFIO, networking, isolation, Sway/Looking Glass, managed Hyprland/Quickshell
   staging and the sleep guard, then owns explicit image/VM/service transactions.
3. This repository records what the architecture is and what has actually been
   proven on hardware.

A green CI run is not a compatibility claim. Hardware status changes only after
the named machine runs the matching frozen commits and evidence gate.

## Hardware status

The Nitro
bootstrap-to-stage-2 host path has been reproduced on the Acer Nitro 5 with an
RTX 3060 Mobile. Within that path,
the normal laptop target adds Sway and the Looking Glass host transport in that
order. Host VFIO and the accelerated Linux video path have real evidence. Final
Linux guest session persistence and Looking Glass input checks are still open.

Both full-pipeline statuses are `pipeline-pending`; historical host/component
results do not qualify the complete current v1 path. An explicit
`no-gpu-passthrough` profile supplies a foundation without VFIO, with no
accelerated desktop or physical single-GPU compatibility claim.

The [v3 acceptance campaign](https://github.com/importriri/hyperlab-ansible/blob/main/docs/release-evidence.md)
is prepared, with qualification pending. Its fixtures add no physical passes;
v2 remains historical and cannot qualify v1. The new host target's convergence,
fresh managed login, Sway recovery and VFIO inhibitor observations still need
their own evidence on the frozen commits.

The Acer Predator Helios 300 with RTX 3070 Mobile has a reviewed profile and
individual component history, but the complete pipeline remains pending until it
replays the same frozen repository commits used for the Nitro release.

See [`hardware/README.md`](hardware/README.md) and
[`hardware/compatibility.yml`](hardware/compatibility.yml).

## Why the problem notes matter

The useful parts of a hardware lab are usually the assumptions that turned out
to be wrong. `problems/` keeps those failures with their symptom, cause, fix and
verification so a future refactor does not have to rediscover them.

Notable examples include PCIe power-management freezes, kvmfr permissions,
Looking Glass display requirements and configuration parsing failures.

## Repository map

- `configs/`: boot, network, libvirt and display contracts;
- `hardware/`: compatibility policy, reports and evidence templates;
- `problems/`: failure investigations;
- `scripts/`: sanitized hardware collection and repository checks;
- [`SETUP.md`](SETUP.md): live-medium-to-lab route, prerequisites and current stops;
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md): symptoms, read-only diagnosis and exact problem-note sources;
- [`FAQ.md`](FAQ.md): short answers about hardware, ISO, recovery, workloads and security;
- [`PROVENANCE-AUDIT.md`](PROVENANCE-AUDIT.md): file origins, candidate
  third-party notices and what is still unresolved;
- [`SECURITY.md`](SECURITY.md): private reporting of vulnerabilities and of
  private data published here by mistake;
- [`EVIDENCE-THREAT-MODEL.md`](EVIDENCE-THREAT-MODEL.md): what the evidence
  here can and cannot establish, and the manual review before publication;
- [`CONTRIBUTING.md`](CONTRIBUTING.md): the checks, write-ups and evidence
  contributions.

Run the repository checks before publishing evidence:

```bash
python scripts/verify_repo.py
bash -n scripts/collect-hardware-report.sh
```

They check consistency only. They are not a privacy review and do not
show that a result happened; see
[`EVIDENCE-THREAT-MODEL.md`](EVIDENCE-THREAT-MODEL.md).

## Scope

The isolated network is for controlled work on systems you own or are authorized
to examine. It has no uplink by default and the host blocks forwarding between
trust domains unless an exposure is explicitly declared.

## Author

[importriri](https://github.com/importriri) is the author and maintainer.
