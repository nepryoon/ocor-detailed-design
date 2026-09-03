# OCOR External Dependency Policy

Every dependency record declares an exact version, authoritative source, license and
cryptographic identity. Mutable tags, floating Python constraints, unauthenticated
mirrors and silent technology substitutions are rejected.

Registry images are referenced by manifest-list digest. A repository-owned image is
permitted only when the required project publishes no suitable official image: its
base image is digest-pinned, its upstream archive checksum is published by the
project, its Dockerfile is reviewed, and its resulting local image ID is captured in
infrastructure evidence.

SBOM and vulnerability scans are retained where practical. A known Critical or High
finding blocks use unless a time-bounded, owner-assigned exception demonstrates that
the vulnerable surface is unreachable. License or terms requiring human acceptance,
external accounts, payment or proprietary access are escalated and never bypassed.
