# Proposed Project Structure

> **Status:** Version 0.1 — proposed repository skeleton. The team should review and freeze the top-level structure during the Day 2 meeting.

```text
sdv-health-monitoring/
├── backend/                    # Spring Boot backend and health engine
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/
│   │   │   └── resources/
│   │   └── test/
│   │       └── java/
│   └── pom.xml
├── vehicle-simulator/          # Kuksa signal and fault simulator
│   ├── src/
│   ├── tests/
│   └── requirements.txt
├── uprotocol/                  # Protobuf schemas and uProtocol integration
│   ├── proto/
│   ├── src/
│   └── tests/
├── ditto/                      # Ditto Thing model and initialization
│   ├── config/
│   └── scripts/
├── opensovd/                   # OpenSOVD configuration and mappings
│   ├── config/
│   └── scripts/
├── frontend/                   # Browser-based monitoring dashboard
│   ├── css/
│   ├── js/
│   ├── tests/
│   └── index.html
├── tests/                      # Cross-component tests
│   ├── integration/
│   ├── e2e/
│   └── postman/
├── docs/                       # Project documentation
│   ├── daily-progress/
│   ├── project-proposal.md
│   ├── work-distribution.md
│   ├── daily-expectations.md
│   ├── vehicle-health-contract.md
│   ├── testing-and-results.md
│   └── github-contribution-guidelines.md
├── docker-compose.yml          # Local multi-component environment
├── Jenkinsfile                # CI pipeline
├── .env.example               # Safe configuration template
├── .gitignore
└── README.md                   # Project overview, setup, and demo instructions
```
