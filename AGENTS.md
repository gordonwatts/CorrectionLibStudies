# Working on this study

This is a new, independent Git repository for histogram lookup nodes loaded by
the experimental native plugin SDK in gordonwatts/correctionlib PR #1.

Run builds, tests, and timings in WSL2 `atlas_al9`. The Windows checkout is
`C:\Users\gwatts\Code\atlas\CorrectionLibStudies`, mounted in WSL at
`/mnt/c/Users/gwatts/Code/atlas/CorrectionLibStudies`.

Read `progress.txt` before continuing. Append decisions, commands, outcomes,
failures, and next steps as work proceeds. Keep enough context to resume without
the original chat. Never present unmeasured numbers as results.

Pin CorrectionLib to PR commit `8dc0b7a8bfe82c15115ff2a5907d4bfa35ee4710`.
Build the core and provider together with the same compiler. Do not alter the
pre-existing study in `/home/gwatts/atlas/correctionlib_tests`.
Each search algorithm belongs in its own `src/nodes/*.cc` file. Shared parsing,
flow handling, and indexing belong in common code so comparisons stay matched.

The SDK returns one double per evaluation. Do not claim cross-output bin reuse,
packed multi-output evaluation, batch SIMD, or a float32 Python API. A reduced
precision node must state exactly which quantities are rounded.

Validate boundaries and invalid inputs before timing. Preserve raw timing rounds,
environment metadata, and build provenance. Use synthetic data without implying
real calibration or full-analysis validation. Keep README language accessible to
a particle physicist and link claims to source and retained evidence.

The user explicitly requested a fresh-context writing review by a sub-agent
running `gpt-6.1-sol` with `high` reasoning after the README is drafted. Pass the
reviewer the audience, README, and source/evidence paths, without the chat history.
