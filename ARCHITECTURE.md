# Healthcare Fraud Detection System - Architecture Diagrams

## Table of Contents
1. [High-Level System Architecture](#high-level-system-architecture)
2. [Data Flow Architecture](#data-flow-architecture)
3. [Component Architecture](#component-architecture)
4. [Deployment Architecture](#deployment-architecture)
5. [Technology Stack Architecture](#technology-stack-architecture)

---

## High-Level System Architecture

```mermaid
graph TB
    subgraph "Users & Interfaces"
        A[Auditors]
        B[Analysts]
        C[API Clients]
        D[Tableau Dashboards]
    end
    
    subgraph "API Gateway Layer"
        E[Load Balancer<br/>ALB/Nginx]
        F[FastAPI Server<br/>Kubernetes Pods]
    end
    
    subgraph "Application Layer"
        G[Fraud Detection<br/>ML Models]
        H[GenAI Assistant<br/>OpenAI GPT-4]
        I[Analytics Engine<br/>Network Analysis]
        J[Alert Manager<br/>Multi-Channel]
    end
    
    subgraph "Data Processing Layer"
        K[Data Pipeline<br/>PySpark]
        L[Feature Engineering<br/>dbt]
        M[Data Validation<br/>Great Expectations]
    end
    
    subgraph "Storage Layer"
        N[(Snowflake<br/>Data Warehouse)]
        O[(S3<br/>Object Storage)]
        P[(PostgreSQL<br/>MLflow DB)]
        Q[(Redis<br/>Cache)]
    end
    
    subgraph "External Services"
        R[OpenAI API]
        S[Snowflake]
        T[AWS Lambda]
        U[CloudWatch]
    end
    
    subgraph "Monitoring & Observability"
        V[Prometheus]
        W[Grafana]
        X[ELK Stack]
    end
    
    A --> D
    B --> D
    C --> E
    D --> E
    E --> F
    F --> G
    F --> H
    F --> I
    F --> J
    G --> K
    H --> K
    I --> K
    K --> L
    L --> M
    M --> N
    M --> O
    G --> P
    F --> Q
    H --> R
    K --> S
    K --> T
    F --> U
    F --> V
    V --> W
    F --> X
    
    style A fill:#e1f5ff
    style B fill:#e1f5ff
    style C fill:#e1f5ff
    style D fill:#e1f5ff
    style G fill:#fff4e1
    style H fill:#e1ffe1
    style N fill:#f0e1ff
    style O fill:#f0e1ff
    style V fill:#ffe1e1
```

---

## Data Flow Architecture

```mermaid
flowchart LR
    subgraph "Ingestion"
        A[Healthcare Claims<br/>Raw Data] --> B[Data Pipeline<br/>Snowflake/S3]
    end
    
    subgraph "Processing"
        B --> C[Feature Engineering<br/>dbt/PySpark]
        C --> D[Data Validation<br/>Quality Checks]
        D --> E[Feature Store<br/>Processed Data]
    end
    
    subgraph "ML Pipeline"
        E --> F[Model Inference<br/>Ensemble]
        F --> G[Fraud Detection<br/>Scoring]
        G --> H[Risk Classification<br/>4 Levels]
    end
    
    subgraph "GenAI Pipeline"
        H --> I[High-Risk Claims<br/>Filter]
        I --> J[GenAI Assistant<br/>GPT-4 Analysis]
        J --> K[Audit Reports<br/>Auto-Generated]
    end
    
    subgraph "Alerting"
        H --> L[Risk Assessment]
        L --> M{Critical?}
        M -->|Yes| N[Immediate Alert<br/>Slack/PagerDuty]
        M -->|No| O[Daily Digest<br/>Email]
    end
    
    subgraph "Storage & Analytics"
        G --> P[(Results DB<br/>Snowflake)]
        K --> Q[Report Store<br/>S3]
        P --> R[Tableau<br/>Dashboards]
        Q --> R
    end
    
    style A fill:#ffe1e1
    style F fill:#fff4e1
    style J fill:#e1ffe1
    style N fill:#ffcccc
    style R fill:#e1f5ff
```

---

## Component Architecture

```mermaid
graph TB
    subgraph "ML Models Component"
        A1[Isolation Forest<br/>Outlier Detection]
        A2[Autoencoder<br/>Reconstruction Error]
        A3[Ensemble<br/>Weighted Voting]
        A1 --> A3
        A2 --> A3
    end
    
    subgraph "GenAI Component"
        B1[LangChain<br/>Orchestration]
        B2[OpenAI GPT-4<br/>LLM]
        B3[Prompts<br/>Templates]
        B1 --> B2
        B3 --> B1
    end
    
    subgraph "API Component"
        C1[FastAPI<br/>REST API]
        C2[Authentication<br/>JWT]
        C3[Rate Limiting<br/>Redis]
        C4[Validation<br/>Pydantic]
        C2 --> C1
        C3 --> C1
        C4 --> C1
    end
    
    subgraph "Data Pipeline Component"
        D1[Snowflake<br/>Source]
        D2[PySpark<br/>Processing]
        D3[dbt<br/>Transform]
        D1 --> D2
        D2 --> D3
    end
    
    subgraph "Monitoring Component"
        E1[Prometheus<br/>Metrics]
        E2[Grafana<br/>Dashboards]
        E3[Alert Manager<br/>Notifications]
        E1 --> E2
        E1 --> E3
    end
    
    A3 --> C1
    B1 --> C1
    C1 --> E1
    D3 --> A3
    
    style A1 fill:#ffe1f0
    style A2 fill:#ffe1f0
    style A3 fill:#ffe1f0
    style B2 fill:#e1ffe1
    style C1 fill:#e1f5ff
    style E2 fill:#ffe1e1
```

---

## Deployment Architecture

```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "VPC"
            subgraph "Public Subnets"
                A[ALB<br/>Load Balancer]
                B[NAT Gateway]
            end
            
            subgraph "Private Subnets"
                subgraph "EKS Cluster"
                    C[API Pods<br/>FastAPI]
                    D[Worker Pods<br/>Processing]
                end
                
                subgraph "Databases"
                    E[RDS PostgreSQL<br/>MLflow DB]
                    F[ElastiCache<br/>Redis]
                end
                
                subgraph "Lambda"
                    G[Claims Processor<br/>Lambda Function]
                end
            end
            
            subgraph "Database Subnets"
                H[S3 Buckets<br/>Data/Models]
            end
        end
        
        subgraph "Services"
            I[Snowflake<br/>Data Warehouse]
            J[OpenAI API<br/>GenAI]
            K[CloudWatch<br/>Monitoring]
        end
    end
    
    subgraph "External"
        L[Users]
        M[CI/CD<br/>GitHub Actions]
    end
    
    L --> A
    A --> C
    C --> E
    C --> F
    G --> H
    C --> I
    C --> J
    C --> K
    M --> C
    
    style A fill:#ff9999
    style C fill:#99ff99
    style E fill:#9999ff
    style H fill:#ffff99
    style I fill:#ff99ff
```

---

## Technology Stack Architecture

```mermaid
graph LR
    subgraph "Frontend & Visualization"
        A[Tableau<br/>Dashboards]
        B[Swagger UI<br/>API Docs]
        C[Grafana<br/>Monitoring]
    end
    
    subgraph "API & Application"
        D[FastAPI<br/>Python 3.11]
        E[Uvicorn<br/>ASGI Server]
        F[Docker<br/>Container]
    end
    
    subgraph "Machine Learning"
        G[PyOD<br/>Anomaly Detection]
        H[Scikit-learn<br/>ML Algorithms]
        I[TensorFlow<br/>Autoencoder]
        J[SHAP<br/>Explainability]
    end
    
    subgraph "GenAI & LLM"
        K[OpenAI GPT-4<br/>LLM]
        L[LangChain<br/>Orchestration]
    end
    
    subgraph "Data Processing"
        M[PySpark<br/>Big Data]
        N[pandas/NumPy<br/>Data Manipulation]
        O[dbt<br/>Transformations]
    end
    
    subgraph "Storage & Databases"
        P[Snowflake<br/>DW]
        Q[AWS S3<br/>Object Storage]
        R[PostgreSQL<br/>MLflow]
        S[Redis<br/>Cache]
    end
    
    subgraph "Infrastructure & IaC"
        T[Kubernetes<br/>Orchestration]
        U[Terraform<br/>IaC]
        V[AWS<br/>Cloud]
    end
    
    subgraph "CI/CD & DevOps"
        W[GitHub Actions<br/>CI/CD]
        X[Prometheus<br/>Metrics]
        Y[CloudWatch<br/>Logging]
    end
    
    A --> D
    B --> D
    C --> D
    D --> G
    D --> H
    D --> I
    D --> J
    D --> K
    D --> L
    D --> M
    D --> N
    D --> O
    D --> P
    D --> Q
    D --> R
    D --> S
    D --> T
    T --> U
    U --> V
    W --> T
    D --> X
    D --> Y
    
    style D fill:#4CAF50
    style K fill:#2196F3
    style P fill:#FF9800
    style T fill:#9C27B0
```

---

## Sequence Diagram - Fraud Detection Flow

```mermaid
sequenceDiagram
    participant U as User/API
    participant A as API Server
    participant D as Data Pipeline
    participant M as ML Models
    participant G as GenAI Assistant
    participant S as Storage
    participant N as Alert System
    
    U->>A: Submit Claim
    A->>D: Fetch & Process Data
    D->>S: Load Features
    S-->>D: Feature Data
    D->>M: Run Inference
    
    M->>M: Isolation Forest
    M->>M: Autoencoder
    M->>M: Ensemble Voting
    M-->>A: Fraud Score
    
    A->>A: Risk Classification
    
    alt High Risk
        A->>G: Generate Analysis
        G->>G: GPT-4 Processing
        G-->>A: Investigation Summary
        A->>S: Save Report
        
        A->>N: Trigger Alert
        N->>N: Slack/PagerDuty/Email
        N-->>U: Immediate Notification
    else Normal Risk
        A->>S: Log Result
        A-->>U: Normal Response
    end
```

---

## Entity Relationship Diagram

```mermaid
erDiagram
    CLAIM ||--o{ CLAIM_LINE : has
    CLAIM ||--|| PROVIDER : from
    CLAIM ||--|| PATIENT : for
    CLAIM ||--o{ DIAGNOSIS_CODE : includes
    CLAIM ||--o{ PROCEDURE_CODE : includes
    CLAIM ||--o{ FRAUD_DETECTION : analyzed_by
    
    PROVIDER ||--o{ CLAIM : submits
    PROVIDER ||--o{ PROVIDER_ANALYTICS : has
    PROVIDER ||--o{ ALERT : triggers
    
    PATIENT ||--o{ CLAIM : has
    
    FRAUD_DETECTION ||--o{ ALERT : generates
    FRAUD_DETECTION ||--o{ REPORT : creates
    
    CLAIM {
        string claim_id PK
        string patient_id FK
        string provider_id FK
        date service_date
        float claim_amount
        int service_count
        string risk_level
        float fraud_probability
        boolean is_fraud
    }
    
    PROVIDER {
        string provider_id PK
        string provider_type
        string specialty
        float risk_score
        int total_claims
        float avg_claim_amount
    }
    
    PATIENT {
        string patient_id PK
        int age
        string gender
        string location
    }
    
    FRAUD_DETECTION {
        string detection_id PK
        string claim_id FK
        timestamp detection_time
        string model_used
        float confidence_score
        json feature_contributions
    }
    
    ALERT {
        string alert_id PK
        string claim_id FK
        string severity
        timestamp created_at
        string status
        string channel
    }
    
    REPORT {
        string report_id PK
        string claim_id FK
        string report_type
        text content
        timestamp generated_at
        string format
    }
```

---

## State Diagram - Claim Processing

```mermaid
stateDiagram-v2
    [*] --> Received: New Claim
    
    Received --> Validating: Start Processing
    Validating --> Validated: Pass Validation
    Validating --> Rejected: Fail Validation
    
    Validated --> FeatureEngineering: Extract Features
    FeatureEngineering --> Scoring: Features Ready
    
    Scoring --> RiskAssessment: Models Complete
    RiskAssessment --> LowRisk: Score < 0.3
    RiskAssessment --> MediumRisk: 0.3 ≤ Score < 0.6
    RiskAssessment --> HighRisk: 0.6 ≤ Score < 0.8
    RiskAssessment --> CriticalRisk: Score ≥ 0.8
    
    LowRisk --> Approved: Auto-Approve
    MediumRisk --> QueueForReview: Manual Review
    HighRisk --> Investigation: Detailed Analysis
    CriticalRisk --> AlertTriggered: Immediate Alert
    
    Investigation --> GenAIAnalysis: Generate Report
    GenAIAnalysis --> ReportGenerated: Report Complete
    
    AlertTriggered --> Investigation: Investigation Started
    QueueForReview --> ManualDecision: Reviewer Decision
    ManualDecision --> Approved: Claim OK
    ManualDecision --> Rejected: Claim Fraud
    
    Approved --> [*]: Process Complete
    Rejected --> [*]: Process Complete
    ReportGenerated --> [*]: Alert Sent
    Rejected --> [*]: Claim Rejected
```

---

## ASCII Architecture Diagrams

### System Architecture (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE LAYER                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Tableau    │  │  Web Portal  │  │ REST API     │  │  Mobile App  │       │
│  │  Dashboards  │  │              │  │  (FastAPI)   │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY LAYER                                      │
│                     ┌─────────────────────────┐                                │
│                     │  Load Balancer (ALB)    │                                │
│                     │  + Rate Limiting         │                                │
│                     │  + SSL/TLS              │                                │
│                     │  + Authentication        │                                │
│                     └─────────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                                      │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    Kubernetes (EKS)                                       │  │
│  │                                                                         │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │  │
│  │  │   API Pods   │  │  Worker Pods │  │  Cron Jobs   │                   │  │
│  │  │   (FastAPI)  │  │ (Processing) │  │ (Scheduled)  │                   │  │
│  │  │              │  │              │  │              │                   │  │
│  │  │  - Auto-scal│  │  - Batch proc│  │  - Retraining│                   │  │
│  │  │  - 3 replicas│  │  - Async jobs│  │  - Reports   │                   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                   │  │
│  │                                                                         │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                ┌───────────────────────┼───────────────────────┐
                ▼                       ▼                       ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│  ML INFERENCE LAYER   │ │   GENAI LAYER        │ │  ANALYTICS LAYER      │
│                       │ │                       │ │                       │
│ ┌─────────────────┐   │ │ ┌─────────────────┐   │ │ ┌─────────────────┐   │
│ │ Isolation Forest │   │ │ │   OpenAI GPT-4  │   │ │ │  Network Graph  │   │
│ │   (PyOD)        │   │ │ │                 │   │ │ │   Analysis     │   │
│ └─────────────────┘   │ │ └─────────────────┘   │ │ └─────────────────┘   │
│ ┌─────────────────┐   │ │ ┌─────────────────┐   │ │ ┌─────────────────┐   │
│ │   Autoencoder   │   │ │ │   LangChain     │   │ │ │  Provider       │   │
│ │  (TensorFlow)   │   │ │ │                 │   │ │ │  Scoring        │   │
│ └─────────────────┘   │ │ └─────────────────┘   │ │ └─────────────────┘   │
│ ┌─────────────────┐   │ │ ┌─────────────────┐   │ │ ┌─────────────────┐   │
│ │    Ensemble     │   │ │ │  Prompt Mgr     │   │ │ │  Pattern        │   │
│ │  (Weighted)     │   │ │ │                 │   │ │ │  Detection      │   │
│ └─────────────────┘   │ │ └─────────────────┘   │ │ └─────────────────┘   │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘
                │                       │                       │
                └───────────────────────┼───────────────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Snowflake   │  │     S3       │  │  PostgreSQL  │  │    Redis     │       │
│  │  (Warehouse) │  │  (Storage)   │  │   (MLflow)   │  │    (Cache)   │       │
│  │              │  │              │  │              │  │              │       │
│  │ - Claims     │  │ - Models     │  │ - Experiments│  │ - Sessions   │       │
│  │ - Features   │  │ - Reports    │  │ - Metrics    │  │ - Query Cache│       │
│  │ - Results    │  │ - Data       │  │ - Artifacts  │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    MONITORING & ALERTING LAYER                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Prometheus  │  │   Grafana    │  │  CloudWatch  │  │   Alert Mgr  │       │
│  │  (Metrics)   │  │ (Dashboards) │  │   (Logs)     │  │ (Multi-Chnl) │       │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘       │
│                            │                       │                          │
│                            ▼                       ▼                          │
│                    ┌──────────────┐       ┌──────────────┐                    │
│                    │     Slack    │       │   PagerDuty  │                    │
│                    └──────────────┘       └──────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow (ASCII)

```
┌─────────────┐
│ Raw Claims  │
│   (CSV/DB)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA INGESTION                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Snowflake  │  │  S3 Upload   │  │  API Ingest   │      │
│  │     Bulk     │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                DATA PROCESSING PIPELINE                      │
│                                                             │
│  Raw Data ──► Validation ──► Cleaning ──► Enrichment        │
│                  │               │            │               │
│                  ▼               ▼            ▼               │
│            Quality Checks   Dedup    Feature Engineering      │
│                                                  │            │
│                                                  ▼            ▼
│  ┌──────────────────────────────────────────────────────┐    │
│  │              FEATURE ENGINEERING                     │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │    │
│  │  │ Numerical  │  │ Categorical│  │  Derived   │     │    │
│  │  │ Features   │  │ Encoding   │  │  Features   │     │    │
│  │  └────────────┘  └────────────┘  └────────────┘     │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    ML INFERENCE                              │
│                                                             │
│  Feature Vector ──► Preprocessing ──► Model Selection        │
│                                      │                      │
│                                      ▼                      │
│                        ┌─────────────────────────┐           │
│                        │    ENSEMBLE MODELS      │           │
│                        │                        │           │
│                        │  ┌────────────────┐     │           │
│                        │  │ Isolation Forest│     │           │
│                        │  └────────────────┘     │           │
│                        │           │            │           │
│                        │  ┌────────────────┐     │           │
│                        │  │   Autoencoder   │     │           │
│                        │  └────────────────┘     │           │
│                        │           │            │           │
│                        │           ▼            │           │
│                        │  ┌────────────────┐     │           │
│                        │  │    Ensemble     │     │           │
│                        │  │ (Weighted Avg) │     │           │
│                        │  └────────────────┘     │           │
│                        └─────────────────────────┘           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                    Fraud Score
                    Risk Level
                     (0.0-1.0)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   Low Risk        Medium Risk      High/Critical
        │                  │                  │
        ▼                  ▼                  ▼
   Auto-Approve      Manual Review      Investigation
        │                  │                  │
        ▼                  ▼                  ▼
   Payment          Review Decision    GenAI Analysis
                                             │
                                             ▼
                                      Audit Report
                                             │
                                          Alerts
                                             │
                                    ┌───────┴───────┐
                                    ▼               ▼
                                 Slack        PagerDuty
```

### Deployment Architecture (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AWS CLOUD                                            │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                            VPC                                       │    │
│  │                                                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │                      Public Subnets                          │    │    │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │    │    │
│  │  │  │  ALB / NGINX │  │  NAT Gateway │  │  Bastion Host │      │    │    │
│  │  │  │              │  │              │  │              │      │    │    │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘      │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                                                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │                     Private Subnets                          │    │    │
│  │  │                                                             │    │    │
│  │  │  ┌─────────────────────────────────────────────────────┐   │    │    │
│  │  │  │              EKS Cluster (Kubernetes)                │   │    │    │
│  │  │  │                                                         │   │    │    │
│  │  │  │  ┌──────────────────┐  ┌──────────────────┐           │   │    │    │
│  │  │  │  │   Control Plane  │  │   Worker Nodes   │           │   │    │    │
│  │  │  │  │                  │  │                   │           │   │    │    │
│  │  │  │  │  - etcd          │  │  ┌────────────┐  │           │   │    │    │
│  │  │  │  │  - API Server     │  │  │ API Pods   │  │           │   │    │    │
│  │  │  │  │  - Scheduler     │  │  │            │  │           │   │    │    │
│  │  │  │  │  - Controller    │  │  │ Worker Pods│  │           │   │    │    │
│  │  │  │  │                  │  │  │            │  │           │   │    │    │
│  │  │  │  └──────────────────┘  │  └────────────┘  │           │   │    │    │
│  │  │  │                         │  (Auto-scaling)  │           │   │    │    │
│  │  │  └─────────────────────────────────────────────┘           │   │    │    │
│  │  │                                                             │   │    │    │
│  │  │  ┌─────────────────────────────────────────────────────┐   │   │    │    │
│  │  │  │              AWS Lambda Functions                    │   │   │    │    │
│  │  │  │  ┌──────────────────────────────────────────────┐   │   │   │    │    │
│  │  │  │  │  Claims Processor                              │   │   │   │    │    │
│  │  │  │  │  - Serverless processing                        │   │   │   │    │    │
│  │  │  │  │  - S3 event triggers                            │   │   │   │    │    │
│  │  │  │  │  - Async processing                             │   │   │   │    │    │
│  │  │  │  └──────────────────────────────────────────────┘   │   │   │    │    │
│  │  │  └─────────────────────────────────────────────────────┘   │   │    │    │
│  │  │                                                             │   │    │    │
│  │  │  ┌─────────────────────────────────────────────────────┐   │   │    │    │
│  │  │  │              Databases & Storage                     │   │   │    │    │
│  │  │  │                                                         │   │    │    │
│  │  │  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │   │    │    │
│  │  │  │  │ RDS          │  │ ElastiCache  │  │   S3       │  │   │   │    │    │
│  │  │  │  │ PostgreSQL   │  │ Redis        │  │ Buckets    │  │   │   │    │    │
│  │  │  │  │              │  │              │  │            │  │   │   │    │    │
│  │  │  │  │ - MLflow DB  │  │ - Cache      │  │ - Data     │  │   │   │    │    │
│  │  │  │  │ - User Data  │  │ - Sessions   │  │ - Models   │  │   │   │    │    │
│  │  │  │  └──────────────┘  └──────────────┘  │ - Reports  │  │   │   │    │    │
│  │  │  │                                        │ - Logs     │  │   │   │    │    │
│  │  │  │                                        └────────────┘  │   │   │    │    │
│  │  │  └─────────────────────────────────────────────────────┘   │   │    │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │    │
│  │                                                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │                   Database Subnets                           │    │    │
│  │  │  ┌──────────────┐  ┌──────────────┐                        │    │    │
│  │  │  │   Snowflake   │  │   External    │                        │    │    │
│  │  │  │   (Managed)   │  │   Services    │                        │    │    │
│  │  │  │               │  │               │                        │    │    │
│  │  │  └──────────────┘  └──────────────┘                        │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                         AWS Services                                  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │ CloudWatch   │  │   SNS        │  │    IAM       │              │    │
│  │  │              │  │              │  │              │              │    │
│  │  │ - Monitoring │  │ - Alerting   │  │ - Security   │              │    │
│  │  │ - Logging    │  │ - Pub/Sub    │  │ - Roles      │              │    │
│  │  │ - Alarms     │  │              │  │              │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Interaction Diagram

```mermaid
graph LR
    subgraph "Data Sources"
        A[Claims DB<br/>Snowflake]
        B[File Upload<br/>S3]
        C[API Input<br/>REST]
    end
    
    subgraph "Processing"
        D[Data Pipeline<br/>PySpark]
        E[Feature Store<br/>dbt]
        F[Validator<br/>Great Expectations]
    end
    
    subgraph "ML Models"
        G[Isolation Forest<br/>PyOD]
        H[Autoencoder<br/>TensorFlow]
        I[Ensemble<br/>Custom]
    end
    
    subgraph "GenAI"
        J[LangChain<br/>Orchestrator]
        K[OpenAI GPT-4<br/>LLM]
    end
    
    subgraph "Outputs"
        L[(Results DB<br/>Snowflake)]
        M[Alerts<br/>Slack/PagerDuty]
        N[Reports<br/>S3]
        O[Dashboard<br/>Tableau]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    F --> H
    G --> I
    H --> I
    I --> J
    I --> L
    I --> M
    J --> K
    K --> N
    L --> O
    N --> O
    
    style G fill:#ff9999
    style H fill:#ff9999
    style I fill:#ff9999
    style K fill:#99ff99
    style L fill:#9999ff
    style O fill:#ffff99
```

---

## Quick Reference

### How to View These Diagrams

1. **GitHub**: These Mermaid diagrams render automatically on GitHub
2. **VS Code**: Install Mermaid Preview plugin
3. **Online**: Use mermaid.live or mermaid-js.github.io/mermaid-live-editor

### Key Architecture Points

1. **Scalability**: Horizontal scaling with Kubernetes
2. **Reliability**: Multi-model ensemble for accuracy
3. **Observability**: Full monitoring stack
4. **Security**: VPC, private subnets, IAM roles
5. **Performance**: Caching, batch processing, async

### Technology Decisions

| Component | Technology | Why? |
|-----------|-----------|------|
| API | FastAPI | Async, fast, type-safe |
| ML | PyOD/TF | Proven, scalable |
| GenAI | OpenAI | Best LLM available |
| Storage | Snowflake | Cloud data warehouse |
| Orchestration | Kubernetes | Industry standard |
| IaC | Terraform | Multi-cloud support |

---

**Last Updated**: 2025-01-22  
**Version**: 1.0.0
