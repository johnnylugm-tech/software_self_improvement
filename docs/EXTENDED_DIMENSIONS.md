# Extended Quality Dimensions

Seven additional dimensions beyond the standard 9. Enabled via `config.advanced.yaml`.

See the [coverage analysis](#coverage-analysis) at the bottom for how these change the automation ceiling.

---

## 1. Mutation Testing

**What**: intentionally breaks your code (mutations), then checks whether tests detect each break. Measures *test strength*, not *test quantity*.

**Why standard coverage is insufficient**:
```
test_coverage 85% + mutation_score 20%  =  most tests are assertions that never fail
test_coverage 70% + mutation_score 80%  =  small but reliable test suite
```

**Tools**:
| Tool | Language | Install |
|---|---|---|
| `mutmut` | Python | `pip install mutmut` |
| `stryker` | JS/TS/Go/C# | `npm i -g @stryker-mutator/core` |

**Prerequisites**:
- Test suite already exists (coverage ≥ 70%)
- Tests run in < 10 min (mutation multiplies this by ×10)

**Score formula**: `(killed_mutants / total_mutants) * 100`

**Default target**: 70 (harder than coverage %)

**Caveat**: slow. Expect 30–90 min per round on a medium codebase.

---

## 2. Property Testing

**What**: replaces hand-written examples with auto-generated inputs that satisfy a *property* (invariant). Explores edge cases example-based tests structurally miss.

**Comparison**:
```python
# Example-based (shows one case)
def test_sort(): assert sort([3,1,2]) == [1,2,3]

# Property-based (validates for ALL integers)
@given(st.lists(st.integers()))
def test_sort_idempotent(xs): assert sort(sort(xs)) == sort(xs)
```

**Tools**:
| Tool | Language | Install |
|---|---|---|
| `hypothesis` | Python | `pip install hypothesis` |
| `fast-check` | JS/TS | `npm i fast-check` |

**Prerequisites**:
- Pure functions or stateless modules exist
- Developer writes at least one property per module (skill generates drafts; human should review)

**Default target**: 75

**Caveat**: LLM-generated properties can themselves be wrong. Always review generated property files before committing.

---

## 3. Fuzzing

**What**: bombards the program with random, malformed, and boundary inputs searching for crashes, memory corruption, or infinite loops. Does *not* check expected behaviour—only whether the program survives.

**Best targets**:
- File parsers (JSON, PDF, image decoders)
- Protocol implementations (network, serialisation)
- Cryptographic primitives
- Any code that accepts untrusted binary input

**Tools**:
| Tool | Language | Install |
|---|---|---|
| `atheris` | Python | `pip install atheris` |
| `jazzer` | Java | [jazzer releases](https://github.com/CodeIntelligenceTesting/jazzer) |
| libFuzzer | C/C++ | `clang -fsanitize=fuzzer` |

**Prerequisites**:
- Project has parsers / binary handlers (fuzzing business logic has very low ROI)
- Build compiled with AddressSanitizer: `CFLAGS="-fsanitize=address,fuzzer"`
- Write fuzz target functions: `def fuzz_target(data: bytes): ...`

**Score formula**: `(fuzz_targets_without_crash / total_fuzz_targets) * 100`

**Default target**: 70

**Caveat**: requires sanitizer-enabled build; runs for hours; not useful for pure business logic layers.

---

## 4. License Compliance

**What**: scans direct and transitive dependencies for licence conflicts, policy violations, and unknown licences. Fully automatable.

**Failure examples**:
```
✗ MIT project  → depends on GPL-3.0 library  → copyleft propagation
✗ Closed-source → depends on AGPL library   → must release source
✗ Enterprise   → 10 dependencies with UNKNOWN licence
```

**Tools**:
| Tool | Type | Install |
|---|---|---|
| `scancode-toolkit` | local CLI | `pip install scancode-toolkit` |
| `fossa` | SaaS | account at fossa.com |
| `license-checker` | Node | `npm i -g license-checker` |

**Prerequisites**:
- Package manifest present (`package.json`, `requirements.txt`, `go.mod`, `Gemfile`, `Cargo.toml`)
- Organisation has defined an allowed/denied licence policy (set in config under `allowed_licenses`)

**Score formula**:
```
100
- 30 per denied-licence violation
- 10 per unknown licence (if fail_on_unknown: false)
- 50 if unable to generate licence report
```

**Default target**: 90

**Caveat**: does not detect post-release supply-chain compromise (a dep that was MIT but was later taken over). That is `supply_chain` territory.

---

## 5. Accessibility (a11y)

**What**: automated detection of WCAG 2.1 AA violations. Covers ~30% of all accessibility issues—the structural, machine-readable ones.

**What it catches**:
- Missing `alt` text on images
- Invalid ARIA roles
- Insufficient colour contrast
- Missing `<label>` on form inputs
- Keyboard-inaccessible interactive elements

**What it cannot catch** (the other 70%):
- Screen reader flow and reading order
- Cognitive load and comprehension
- Motor-impaired navigation patterns
- Actual usability for blind/deaf/motor-impaired users

**Tools**:
| Tool | Install |
|---|---|
| `axe-core` | `npm i -g @axe-core/cli` |
| `pa11y` | `npm i -g pa11y` |

**Prerequisites**:
- Frontend project (HTML / React / Vue / Angular)
- Browser automation available (Playwright/Puppeteer) OR a running dev server
- Define `base_url` and `urls` list in config

**Score formula**: `100 - min(violations * 5, 100)` (weighted by severity)

**Default target**: 85

**Critical note**: a score of 85 on this dimension means *no automated violations detected*. It does **not** mean the application is accessible to real users with disabilities.

---

## 6. Observability

**What**: LLM-judges source code for instrumentation quality:
- Log statements carry enough context (not just `"error occurred"`)
- Error paths are logged before propagating
- No sensitive data in logs (passwords, tokens, PII)
- Critical paths have trace spans
- Metrics are named consistently

**Why LLM-only**:
No static tool can tell whether your log statements produce *useful signals* in production. This is a judgement call requiring code reading.

**Prerequisites**:
- Project uses a logging library (`structlog`, `winston`, `zap`, `slog`, `logrus`)
- Key paths instrumented with metrics or traces

**Score formula**: start 100, subtract per systemic issue found:
- No log in error path: −8
- Missing context in log (e.g., no request ID): −5 per occurrence
- PII/secret in log: −20
- Missing trace span on critical path: −10
- Inconsistent metric naming: −3

**Default target**: 75 (lower because pure LLM-judge, higher uncertainty)

**Critical limitation**: this evaluates source code, **not** production signals. A score of 85 means code *looks* well-instrumented. Whether those signals are actually useful in an incident requires production log analysis.

---

## 7. Supply Chain Security

**What**: generates a Software Bill of Materials (SBOM), scans it for CVEs, and optionally verifies artifact provenance via Sigstore.

**Three layers**:
| Layer | Tool | What it checks |
|---|---|---|
| SBOM generation | `syft` | Lists every dependency + version |
| CVE scan | `grype` | Maps SBOM against NVD/OSV databases |
| Provenance | `cosign` (sigstore) | Verifies artifact was signed by expected CI identity |

**Prerequisites**:
- Docker image, language package, or source directory
- `brew install syft grype` (or equivalent)
- For sigstore: CI/CD with OIDC provider (GitHub Actions, GitLab CI)

**Score formula**:
```
100
- 40 per critical CVE
- 20 per high CVE
- 10 per medium CVE
- 20 if SBOM cannot be generated
- 30 if sigstore_verify: true AND no valid attestation found
```

**Default target**: 85

**Caveat**: detects *known* CVEs. Zero-days and novel supply-chain attacks (e.g., a maintainer going rogue and publishing a malicious patch) are outside what any automated tool can catch.

---

## Coverage Analysis

How these 7 dimensions change the automation ceiling:

| Dimension | Automation gain | What still requires humans |
|---|---|---|
| **Mutation testing** | +5% | Whether the property under test is the *right* property |
| **Property testing** | +3% | Whether the property itself is correct |
| **Fuzzing** | +3% | Business logic bugs; design flaws |
| **License compliance** | +3% | Post-release supply-chain compromise |
| **Accessibility** | +1% | 70% of a11y; real user experience |
| **Observability** | +2% | Whether signals are useful in production |
| **Supply chain** | +3% | Zero-days; novel adversarial attacks |
| **Total gain** | **+15–20%** | |

**Revised assertion** (from `docs/ANTI_BIAS.md`):

> Standard 9 dimensions automate 60–70% of observable quality checks.
> With the 7 extended dimensions enabled, the ceiling rises to **75–80%**.
> The remaining 15–20% requires production signals, domain experts, real users,
> and real attackers—data sources no tool can substitute.

### The invariant that doesn’t change

Every dimension in this framework reads source code and tool output.
The 7 extended dims read *more* of it, more deeply.
But none creates knowledge from outside the codebase:

- Business logic correctness (“is this the right behaviour?”) lives in domain expertise, not source code.
- Real user experience lives in user behaviour, not WCAG rule violations.
- Zero-day vulnerabilities are definitionally unknown to any scanner.
- Production signal quality lives in production, not in log.info() call sites.

*Auto-research can run unlimited rounds. It still cannot observe what it has never been given to observe.*
