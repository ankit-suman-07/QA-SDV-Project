# Iteration 2 Task Distribution

## Purpose

This document assigns the work required for **Iteration 2: System Extension, Validation, and Evaluation**.

The selected extension is a **configurable vehicle-signal publication rate**. The team will run the pipeline at multiple rates and measure latency, throughput, delivery success, and digital-twin reliability.

## Experiment Contract

The team will evaluate three publication intervals:

| Condition | Publication interval |
|---|---:|
| Baseline | 5.0 seconds |
| Medium load | 1.0 second |
| High load | 0.2 seconds |

Each experiment should use the same number of messages. The recommended sample size is **100 messages per condition**.

The final results should include:

- Minimum latency
- Average latency
- Median latency
- 95th-percentile latency
- Maximum latency
- Throughput
- Successful-update rate
- Missing or duplicate message count

---

## Ankit Suman

### Role

**Integration, Measurement and Quality Lead**

### Suggested branch

```text
feature/iteration2-pipeline-evaluation
```

### Tasks

1. Define and approve the shared experiment configuration and CSV fields.
2. Remove repository artifacts that should not be submitted:
   - `tmp/`
   - `.venv/`
   - `.venv-1/`
   - `.DS_Store`
   - `__pycache__/`
   - Generated build directories such as `target/`
   - Unnecessary nested `.git/` directories
3. Confirm all temporary paths are covered by `.gitignore`.
4. Update `ditto/scripts/interim-kuksa-to-ditto-bridge.py` after the uProtocol transport is relocated.
5. Refactor the bridge into testable functions for:
   - Reading Kuksa state
   - Publishing and receiving the Protobuf event
   - Evaluating vehicle health
   - Updating Ditto
   - Recording measurements
6. Measure pipeline latency with `time.perf_counter()`.
7. Start measurement before processing the Kuksa state and stop after Ditto confirms the update.
8. Validate each Ditto response with `raise_for_status()`.
9. Record each event in CSV with:
   - Experiment ID
   - Event ID
   - Publication interval
   - Start timestamp
   - Completion timestamp
   - Latency in milliseconds
   - Success or failure
   - Health status
10. Calculate all required summary statistics.
11. Write automated tests for:
    - Successful processing
    - Ditto failure
    - CSV recording
    - Latency calculation
    - p95 calculation
    - Preservation of low-battery behaviour
12. Coordinate the final experiment runs with Atharva.
13. Review and integrate the team pull requests in dependency order.

### Deliverables

- Refactored integration bridge
- Latency and result-recording implementation
- Integration and measurement tests
- Raw experiment CSV files
- Summary results
- Clean integrated repository

### Acceptance criteria

- Every processed event produces one measurement record.
- Failed Ditto requests are recorded.
- All automated tests pass.
- The pipeline works at all three publication rates.
- No temporary runtime or environment directories are committed.

---

## Emmanuel Adegboye

### Role

**Simulator and Load Extension Lead**

### Suggested branch

```text
feature/configurable-simulator-rate
```

### Tasks

1. Add a `PUBLISH_INTERVAL_SECONDS` environment variable.
2. Replace the fixed `time.sleep(5)` in `vehicle-simulator/src/main.py`.
3. Use `5.0` seconds as the default interval.
4. Reject non-numeric, zero, or negative interval values.
5. Add the environment variable to `vehicle-simulator/docker-compose.yml`.
6. Support `5.0`, `1.0`, and `0.2` second experiment intervals.
7. Preserve both normal and low-battery fault modes.
8. Preserve the agreed Kuksa/VSS signal paths.
9. Add the publication timestamp, operating mode, and configured interval to simulator logs.
10. Refactor interval parsing into a testable function.
11. Write tests for:
    - Default interval
    - Valid custom interval
    - Invalid interval
    - Normal signal generation
    - Fault signal generation
12. Verify that all four signals reach Kuksa at every rate.
13. Update `vehicle-simulator/README.md` with the experiment commands.

### Deliverables

- Configurable publication rate
- Updated Docker Compose configuration
- Simulator configuration tests
- Logs or screenshots for all three rates
- Updated simulator documentation

### Acceptance criteria

- The rate changes without editing Python source code.
- Invalid intervals generate a clear error.
- All four signals continue reaching Kuksa.
- Normal and fault modes remain operational.

---

## Benjamin Emeshili

### Role

**Protobuf Transport and Delivery Validation Lead**

### Suggested branch

```text
feature/message-traceability
```

### Tasks

1. Move the transport implementation from:

```text
eclipse-components/ditto/uprotocol_transport.py
```

to:

```text
uprotocol/transport.py
```

2. Add `uprotocol/__init__.py` if required.
3. Update the Ditto bridge to import the transport from its new location.
4. Ensure the bridge runs from the repository root without manually changing `PYTHONPATH`.
5. Preserve the existing Protobuf schemas and generated classes.
6. Ensure every event contains:
   - Unique event ID
   - Vehicle ID
   - Source timestamp
   - Publication timestamp
7. Record a reception timestamp after deserialization.
8. Implement delivery tracking for:
   - Published messages
   - Received messages
   - Duplicate event IDs
   - Missing event IDs
   - Invalid messages
9. Write tests for:
   - Serialization and deserialization
   - Matching event IDs
   - Unique event IDs
   - Timestamp preservation
   - Corrupted-message rejection
   - Duplicate detection
10. Expose delivery statistics to Ankit's experiment recorder.
11. Update `uprotocol/README.md`.
12. Clearly document that the current implementation uses an in-process Protobuf/uProtocol-compatible transport.

### Deliverables

- Properly located transport module
- Correct bridge imports
- Message-delivery tracker
- Extended transport tests
- Updated uProtocol documentation

### Acceptance criteria

- The bridge starts from the repository root without import errors.
- Every valid message is traceable through its event ID.
- Duplicate and invalid messages are detected.
- Published and received counts are available.
- All transport tests pass.

---

## Atharva Rajadhyaksha

### Role

**Eclipse Ditto and Runtime Validation Lead**

### Suggested branch

```text
feature/ditto-experiment-validation
```

### Tasks

1. Maintain the top-level Ditto structure:

```text
ditto/
├── config/
├── scripts/
└── README.md
```

2. Validate:
   - `ditto/config/vehicle-001-thing.json`
   - `ditto/config/vehicle-policy.json`
3. Ensure the Ditto Thing represents:
   - Vehicle ID
   - Current signals
   - Health status
   - Active faults
   - Source timestamp
   - Synchronization timestamp
4. Update the model if timestamps are missing.
5. Ensure `ditto/README.md` explains:
   - Obtaining Ditto
   - Starting and stopping Ditto
   - Creating the policy and Thing
   - Running the bridge
   - Verifying the Thing
6. Do not include the complete Eclipse Ditto source repository or `tmp/`.
7. Create `ditto/scripts/verify-vehicle-state.py`.
8. Make the verification script:
   - Query `sdv:vehicle-001`
   - Validate required signal fields
   - Validate health fields
   - Detect missing or stale values
   - Return a non-zero exit code on failure
9. Add mocked tests for the verifier.
10. Run Ditto validation at all three publication rates.
11. Record:
    - Expected updates
    - Successful updates
    - Failed updates
    - Final twin state
    - Missing or stale values
12. Verify that low battery still produces `WARNING` and `BATTERY_LOW`.
13. Capture normal, high-rate, and fault-state API evidence.
14. Optionally record supporting CPU and memory observations using `docker stats`.

### Deliverables

- Valid Ditto configuration
- Updated Ditto README
- Ditto verification script and tests
- Validation results for all experiment conditions
- API evidence

### Acceptance criteria

- Ditto can be installed without the repository's `tmp` folder.
- Policy and Thing creation commands work.
- The digital twin contains the latest state after each experiment.
- Missing or stale state is detected.
- The existing fault response remains correct.

---

## Mehtaj

### Role

**Documentation, Results and Demonstration Lead**

### Suggested branch

```text
feature/iteration2-documentation
```

### Tasks

1. Update the root `README.md` to use:
   - `ditto/config/vehicle-policy.json`
   - `ditto/config/vehicle-001-thing.json`
   - `ditto/scripts/interim-kuksa-to-ditto-bridge.py`
2. Remove outdated references to `eclipse-components/ditto/`.
3. Remove instructions that require the submitted `tmp/` folder.
4. Document:
   - Normal operation
   - Fault operation
   - Publication-rate configuration
   - Experiment execution
   - Test execution
   - Result generation
5. Agree with Ankit on the CSV column names.
6. Create a result-processing script.
7. Generate a comparison table containing:

| Interval | Messages | Average latency | p95 latency | Maximum latency | Throughput | Success rate |
|---|---:|---:|---:|---:|---:|---:|

8. Generate at least one chart comparing publication rate with latency or throughput.
9. Verify every chart value against the raw CSV files.
10. Organize evidence under:

```text
docs/evidence/iteration-2/
```

11. Prepare report sections covering:
    - System extension
    - Experiment methodology
    - Functional validation
    - Results
    - Analysis
    - Limitations
12. Update the architecture diagram only if the implemented architecture changes significantly.
13. Prepare the 3-5 minute demonstration script.
14. Ensure screenshots exclude unrelated errors, personal paths, and unnecessary terminal output.

### Deliverables

- Corrected root README
- Experiment reproduction instructions
- Results-processing script
- Final comparison table and chart
- Organized evidence
- Report content
- Demonstration plan

### Acceptance criteria

- A new user can reproduce the experiment from the README.
- Documentation contains no outdated paths.
- Tables and charts match the raw CSV data.
- The report includes the required analysis.
- The demonstration fits within 3-5 minutes.

---

## Dependency and Integration Order

1. Ankit cleans the repository and finalizes the experiment contract.
2. Emmanuel implements configurable signal publication rates.
3. Benjamin relocates the transport and adds message tracking.
4. Ankit integrates the extensions and adds latency measurement.
5. Atharva validates Ditto and runs the experiment with Ankit.
6. Mehtaj produces the table, chart, README updates, report content, and demonstration material.

## Iteration 2 Requirement Coverage

| Requirement | Assigned work |
|---|---|
| Meaningful system extension | Configurable signal publication rate - Emmanuel |
| Functional validation | Message validation - Benjamin; Ditto validation - Atharva |
| Non-functional measurement | Latency, throughput and success rate - Ankit |
| Structured experiment | Three publication rates - Ankit, Emmanuel and Atharva |
| Table or chart | Results processing and visualization - Mehtaj |
| Written analysis | Experiment analysis - Ankit and Mehtaj |
| Updated README | Mehtaj, with component-owner review |
| Updated repository | All members through separate branches and pull requests |
| Demonstration video | Mehtaj using evidence supplied by the team |

## Team Working Rules

- Each member works on a separate branch.
- Tests should be written before or alongside implementation.
- Every pull request must identify its deliverables and test evidence.
- Component owners must update their own README or documentation.
- Raw experiment data must not be manually edited.
- Temporary environments, full external source repositories, and generated cache files must not be committed.
