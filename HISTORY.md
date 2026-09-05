# Development history

This repository consolidates the API, worker, dashboard and WaveAgent repositories.
Their genuine development commits retain their original author and committer dates.
Contributor aliases have been normalized. Commit subjects carry component prefixes;
vague subjects have been clarified using the files changed. Consolidation and new
platform changes are committed at the time the work is performed.

History was rewritten to remove credential literals, private environment files,
service-account files, database snapshots and generated Python caches. Rewriting
changes commit hashes and invalidates old commit signatures. The original repositories
remain separately backed up; they must not be pushed into this public repository.
The Python SDK remains a separate distribution.

Secret scans cover the rewritten history and the release tree. Removing a credential
from Git does not revoke it; credential rotation remains a separate owner-controlled
operation before publication. Scanner success is one check, not a guarantee that
all sensitive information has been identified.
