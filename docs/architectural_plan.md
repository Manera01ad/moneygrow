# MoneyGrow Modernization: Final Architectural Plan

This document outlines the definitive strategy for enhancing the MoneyGrow application, focusing on user authentication, backend orchestration, and frontend modernization.

---

### **Phase 1: Full User Authentication & API Key Management**

*   **Objective:** Implement a complete authentication system where users can register, log in, and manage their own API keys.
*   **Key Components:**
    1.  **Database Models (`src/models/database.py`):**
        *   A `User` table for credentials (`email`, `hashed_password`).
        *   An `APIKey` table linked to the `User` table.
        *   The `AnalysisTask` table will be linked to a `user_id`.
    2.  **Authentication API (`src/api/auth.py`):**
        *   Endpoints for `/register` and `/token` (login).
        *   Will use JWT for session management.
    3.  **User Management API (`src/api/users.py`):**
        *   Protected endpoints for users to manage their profile and generate/revoke their own API keys (e.g., `GET /users/me`, `POST /users/me/api-key`).
    4.  **Security Logic (`src/api/security.py`):**
        *   A dependency that validates the `X-API-KEY` header against the database and returns the full `User` object on success.

*   **Architectural Diagram: User Authentication & API Key Flow**
    ```mermaid
    sequenceDiagram
        participant Client
        participant "Auth API (/auth)"
        participant "Users API (/users)"
        participant "Analysis API (/analysis)"
        participant "Security Module"
        participant Database

        Client->>+Auth API (/auth): POST /register (email, pass)
        Auth API (/auth)->>+Database: Create User
        Database-->>-Auth API (/auth): User Created
        Auth API (/auth)-->>-Client: 201 Created

        Client->>+Auth API (/auth): POST /token (email, pass)
        Auth API (/auth)-->>-Client: JWT Access Token

        Client->>+Users API (/users): POST /me/api-key (JWT Auth)
        Users API (/users)->>+Database: Create APIKey for User
        Database-->>-Users API (/users): APIKey Created
        Users API (/users)-->>-Client: { "api_key": "user_specific_key" }

        Client->>+Analysis API (/analysis): POST /analysis (X-API-KEY: user_specific_key)
        Analysis API (/analysis)->>+Security Module: Validate Key
        Security Module->>+Database: Find Key & User
        Database-->>-Security Module: User Found
        Security Module-->>-Analysis API (/analysis): User Object
        Analysis API (/analysis)-->>-Client: 202 Accepted
    ```

---

### **Phase 2: Enhance Orchestration with Agent-Based Tasks**

*   **Objective:** Refactor the monolithic analysis task into a flexible, agent-based system.
*   **Key Components:**
    1.  **Agent Tasks (`src/tasks/workers.py`):** Create separate Celery tasks for `HeuristicAnalysisAgent`, `MLPredictionAgent`, and `SmartMoneyAgent`.
    2.  **Orchestrator Task:** The main `_run_analysis_task` will be refactored to call these agent tasks in parallel using a Celery `group`.

*   **Architectural Diagram: Orchestration Flow**
    ```mermaid
    graph TD
        subgraph "Current Orchestration (Monolithic)"
            A[run_analysis_task] --> B(Collect Data);
            B --> C(Heuristic Checks);
            C --> D(ML Prediction);
            D --> E(Smart Money);
            E --> F(Combine & Save);
        end

        subgraph "Proposed Orchestration (Agent-Based)"
            O1[Orchestrator Task] --> O2(Collect Data);
            O2 --> P(Run Agent Group in Parallel);
            subgraph "Parallel Agents (Celery Group)"
                P1[HeuristicAgent]
                P2[MLAgent]
                P3[SmartMoneyAgent]
            end
            P --> O3(Collect & Combine Results);
            O3 --> O4(Save Final Report);
        end
    ```

---

### **Phase 3: Modernize the Frontend with React**

*   **Objective:** Build a modern, dynamic, and user-friendly interface.
*   **Key Components:**
    1.  **New React Project:** Initialize a new React + TypeScript project in `frontend/client`.
    2.  **Authentication UI:** Create pages and components for user registration, login, and a dashboard for API key management.
    3.  **Component Architecture:** Decompose the UI into reusable components for the analysis form, status tracking, and results display.
    4.  **State Management:** Utilize a library like React Query (TanStack Query) to manage API interactions, including polling for analysis status.

*   **Architectural Diagram: React Component Hierarchy**
    ```mermaid
    graph TD
        subgraph "React Frontend (frontend/client)"
            App[App.tsx] --> PageLayout;
            PageLayout --> Header;
            PageLayout --> Footer;
            PageLayout --> AnalysisPage;

            AnalysisPage -- Manages State --> AuthPages[Login/Register Pages];
            AnalysisPage -- Manages State --> DashboardPage[User Dashboard];
            AnalysisPage -- Manages State --> AnalysisForm;
            AnalysisPage -- Manages State --> StatusTracker;
            AnalysisPage -- Manages State --> ResultsDisplay;

            StatusTracker --> ProgressStep[ProgressStep Component];
            ResultsDisplay --> RiskScore[RiskScore Component];
            ResultsDisplay --> HeuristicRisks[HeuristicRisks Component];
            HeuristicRisks --> RiskCard[RiskCard Component]
            ResultsDisplay --> MLPrediction[MLPrediction Component];
            ResultsDisplay --> SmartMoney[SmartMoney Component];
        end