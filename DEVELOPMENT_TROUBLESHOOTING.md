# Nexora --- Development Issues and Resolutions

This document records the main implementation issues encountered while
building Nexora, how they were investigated, and what was changed to
resolve them. It is intended to provide a transparent engineering
history for the project repository.

> **Scope note:** This is a retrospective based on the development and
> testing history recorded for this project. It documents the issues
> that were actually encountered or observed. It does not claim that
> every possible failure mode has been tested.

## 1. Groq token-per-minute limit during multi-tool orchestration

**Symptom**

A comprehensive request that required several HR capabilities in one
investigation failed during orchestration. Groq returned a
token-per-minute limit error. The request was attempting to process a
large amount of tool output, and the reported request size was slightly
above the available token budget (first 8,192 tokens, then 8,177 tokens
against an 8,000 TPM limit).

**Cause**

The LangGraph workflow could call multiple tools in sequence. Large
database results were being added to the model context, increasing
prompt size and token consumption.

**Resolution**

-   Increased the maximum allowed tool rounds from 5 to 10 so a
    multi-capability investigation had enough steps to complete.
-   Added tool-result compaction in the LangGraph tool node.
-   Reduced the default retained record count to one for tools where a
    concise result was sufficient.
-   Preserved full results for tools where complete records were needed
    to answer the user's question, including:
    -   `workforce_overview`
    -   `project_staffing_analysis`
    -   `project_workforce_risks`
    -   `employee_workload_analysis`
    -   `employee_workforce_risks`

**Verification**

The integrated five-capability investigation subsequently completed with
HTTP 200 and reported `LangGraph` as the orchestration path.

**Engineering lesson**

Tool outputs should be sized according to the question. Compacting every
result indiscriminately can hide records needed for accurate answers;
passing every record to the model can exceed provider limits.

## 2. Tool-result compaction hid department headcounts

**Symptom**

The question asking for employee headcount by department initially
returned only one department (Marketing) instead of all departments.

**Cause**

The `workforce_overview` result was being compacted too aggressively.
The model received an incomplete department list.

**Resolution**

Added `workforce_overview` to the `FULL_RESULT_TOOLS` pass-through set
in `app/graph_orchestrator.py`, so the complete department breakdown
reaches the model.

**Verification**

The chatbot returned all eight departments:

  Department                 Employees
  ------------------------ -----------
  Marketing                         32
  Engineering                       30
  Sales                             26
  Information Technology            25
  Human Resources                   23
  Finance                           23
  Customer Support                  22
  Operations                        19
  **Total**                    **200**

## 3. Project staffing response omitted an understaffed project

**Symptom**

The first chatbot staffing response identified PROJ002 but did not show
PROJ005, even though both projects were understaffed.

**Cause**

The relevant project-risk tool output was being compacted, so the model
did not receive the complete set of project staffing records needed for
the response.

**Resolution**

Added `project_workforce_risks` to `FULL_RESULT_TOOLS` in
`app/graph_orchestrator.py`.

**Verification**

The chatbot subsequently identified both projects:

  Project                                        Required   Assigned     Shortage
  -------------------------------------------- ---------- ---------- ------------
  PROJ002 --- Employee Experience Initiative           14         10            4
  PROJ005 --- Financial Reporting System               11          9            2
  **Combined shortage**                                                **6 FTEs**

## 4. Employee workload response showed only one employee

**Symptom**

The first workload response showed only a single employee, despite the
database analysis identifying multiple employees assigned to more than
one active project.

**Cause**

The `employee_workforce_risks` result was being compacted before the
model could use the full employee list.

**Resolution**

Added `employee_workforce_risks` to `FULL_RESULT_TOOLS` in
`app/graph_orchestrator.py`.

**Verification**

The chatbot returned all 18 employees with multiple active project
assignments. The summary reported 168 active employees analyzed and zero
employees above 100% allocation.

## 5. Annual-leave balance lookup failed because leave-type labels differed

**Symptom**

A date-specific annual-leave review for Kimberly Perez (EMP0027)
initially failed to retrieve the expected annual-leave balance, even
though the database contained an annual-leave balance of 20 days.

**Cause**

The stored leave-type label and the requested leave-type label did not
match exactly. The database could contain a label such as
`Annual Leave`, while the request used `Annual`.

**Resolution**

Updated the leave-balance SQL comparison in
`app/services/hr_workflow_intelligence.py` to normalize both values
by: - converting to lowercase; - trimming surrounding whitespace; and -
removing a trailing `leave` suffix.

The comparison uses PostgreSQL `REGEXP_REPLACE` on both the stored and
requested leave type.

**Verification**

The review retrieved the expected 20-day annual-leave balance for
Kimberly Perez.

## 6. Leave date-conflict validation needed to be independent of balance lookup

**Symptom**

The leave workflow needed to check date overlaps for pending and
approved requests, including when a balance record could not be found. A
balance lookup failure should not prevent the system from checking dates
supplied by the employee.

**Cause**

Balance validation and date-conflict validation are separate checks.
Coupling the conflict check to a successful balance lookup could cause
the system to omit an important validation result.

**Resolution**

Updated `review_leave_workflow()` so that, when both dates are supplied,
it independently queries leave requests for the same employee where: -
status is `PENDING` or `APPROVED`; - start and end dates are present;
and - the existing date range overlaps the requested date range.

The overlap condition is:

``` sql
start_date <= requested_end_date
AND end_date >= requested_start_date
```

The function also validates that both dates are supplied together,
parses ISO dates, and rejects an end date earlier than the start date.

**Verification**

For Kimberly Perez's request from November 16--20, 2026, the tool
reported that the date-conflict check was performed and found no
overlapping pending or approved requests.

## 7. Leave workflow did not block a request when the required manager was missing

**Symptom**

The initial leave review could pass balance and policy checks even
though Kimberly Perez had no manager assigned. A request requiring
manager approval must not be treated as ready for submission when no
approver is available.

**Cause**

Passing leave balance and policy checks is not sufficient to establish
that a request can proceed through its approval workflow.

**Resolution**

Updated the leave workflow review to evaluate manager-approval
requirements and manager assignment. When manager approval is required
and the employee has no assigned manager, the workflow returns: -
`BLOCKED_MISSING_APPROVER`; - `approval_blocked: true`; and -
`submission_ready: false`.

**Verification**

Kimberly's five-day annual-leave review returned
`BLOCKED_MISSING_APPROVER`. Nexora stated that the request could not be
routed and confirmed that it had not been submitted or approved.

**Remaining validation boundary**

The implemented check verifies that a manager ID is present. The
development history does not establish that the manager record is
independently validated as active and authorized for the specific
approval. That should be treated as a future hardening task, not as a
completed feature.

## 8. Integrated investigation initially reached the tool-call limit

**Symptom**

A single question asking Nexora to investigate an employee across
several HR capabilities initially stopped after reaching the configured
maximum tool rounds.

**Cause**

The workflow's maximum tool-call iteration count was 5, which was
insufficient for the multi-step investigation.

**Resolution**

Raised `MAX_TOOL_ROUNDS` to 10 in `app/graph_orchestrator.py`.

**Verification**

After the tool-round increase and tool-result compaction changes, the
integrated investigation completed successfully and returned results
from the relevant HR capabilities.

## 9. Chat interface displayed Markdown tables as raw text

**Symptom**

Backend answers containing Markdown tables and lists appeared in the
browser with literal pipe characters and Markdown syntax instead of a
formatted table or list.

**Cause**

The original frontend `formatAnswer()` function split the response into
lines and rendered each line as a paragraph. It handled basic bold text
and inline code but did not parse Markdown block structures.

**Resolution**

Updated `frontend/src/App.jsx` with a Markdown-aware renderer for: -
tables; - ordered and unordered lists; - headings; - bold and italic
text; - inline code and fenced code blocks; - blockquotes; and -
horizontal dividers.

**Verification**

The employee headcount response was tested in the browser and the table
appeared properly formatted.

## 10. Frontend-to-backend integration and local development setup

**Observed setup issue / integration requirement**

The React/Vite frontend needed to send chat requests to the FastAPI
backend without hardcoding a separate browser-facing backend URL in the
chat component.

**Resolution**

Configured the Vite development server proxy in
`frontend/vite.config.js`:

``` javascript
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
}
```

The frontend sends requests to `/api/assistant/chat`, and Vite forwards
them to the FastAPI backend.

**Verification**

The frontend successfully sent a question to Nexora and received a
database-backed answer. The backend and frontend were run locally on
ports 8000 and 5173 respectively.

## 11. Predictive assessment output did not show every high-risk project

**Observed limitation**

The comprehensive predictive assessment reported: - 11 projects
analyzed; - 2 high-risk projects; - 0 medium-risk projects; and - 9
low-risk projects.

However, the detailed project list displayed only PROJ002, even though
earlier staffing and predictive tests had identified PROJ005 as another
high-risk project.

**Interpretation**

The aggregate risk counts were present, but the detailed records were
limited by the returned result set. The response itself acknowledged
that another high-risk project was omitted.

**Status**

This was observed during final testing and was not fully resolved in the
recorded development work. A future improvement is to return all
high-risk project records (or at least all records in the requested risk
category) while keeping lower-risk records compacted.

## 12. Predictive scoring was clarified as rule-based, not machine learning

**Potential interpretation risk**

The capability is named Predictive Workforce Intelligence, which could
lead users to assume it uses a trained machine-learning model.

**Resolution**

The orchestration system prompt and test prompts explicitly distinguish
the implemented explainable, deterministic rule-based scoring from
statistical forecasting or trained machine-learning predictions. Nexora
is instructed not to claim that an employee will leave or a project will
fail based only on risk indicators.

**Verification**

The final predictive assessment described the scoring engine as
rule-based and explicitly stated that no trained machine-learning
forecast was being used.

## 13. Actual leave submission and notification were kept outside the implemented scope

**Observed capability boundary**

The leave workflow validates a request and determines whether it is
ready for approval routing. It does not submit or approve leave
requests, assign managers, or send notifications.

**Resolution**

The workflow and system instructions were kept within a decision-support
scope: - review leave balance and policy; - check date conflicts when
dates are provided; - identify approval requirements and missing
approvers; - report whether the request is blocked or preliminarily
passed; and - never claim that a request was submitted or approved.

**Verification**

The Kimberly Perez test explicitly returned a blocked status and
confirmed that no leave had been submitted or approved.

## 14. Summary of final capability tests

The following end-to-end chatbot tests were completed during final
verification:

  -----------------------------------------------------------------------
  Capability                          Observed test result
  ----------------------------------- -----------------------------------
  Organizational Intelligence         Examined 200 employee records and
                                      reported 162 records flagged for
                                      missing manager assignments.

  Approval Routing Intelligence       Examined 93 pending leave requests
                                      and reported 73 routing issues; one
                                      detailed issue was displayed.

  Workforce Intelligence              Analyzed 11 active projects,
                                      identified PROJ002 and PROJ005 as
                                      understaffed with a combined
                                      shortage of 6 FTEs, and reported 18
                                      employees with multiple project
                                      assignments and zero overallocated
                                      employees.

  Context-Aware HR Workflow           Reviewed Kimberly Perez's five-day
                                      annual-leave request, checked
                                      balance, policy, dates and approval
                                      requirements, and blocked it
                                      because no manager was assigned.

  Predictive Workforce Intelligence   Analyzed 11 projects and 168
                                      employees using explainable
                                      rule-based scoring; reported two
                                      high-risk projects and no high- or
                                      medium-risk employees. The detailed
                                      project output omitted one
                                      high-risk project.
  -----------------------------------------------------------------------

## 15. Known limitations and future improvements

The following points should be described as limitations or future work
rather than completed functionality:

1.  **Full risk-record retrieval:** Ensure every high-risk project is
    included in detailed predictive output.
2.  **Approval authorization validation:** Verify that an assigned
    manager exists, is active, and is authorized to approve the relevant
    leave type.
3.  **Leave submission and approval:** Implement only with explicit
    authorization, audit logging, and appropriate HR controls.
4.  **Notifications:** Integrate an email or notification service before
    claiming that employees or managers can be notified automatically.
5.  **Conversation persistence:** The current frontend conversation
    history is held in React state and is lost when the page is
    reloaded.
6.  **Frontend navigation:** The intelligence labels in the sidebar are
    visual navigation elements; they are not separate implemented
    dashboard pages.
7.  **Predictive modeling:** The current risk engine is rule-based. A
    trained forecasting model would require a separate dataset,
    training, evaluation, and validation process.
8.  **HR decision oversight:** Risk scores and workflow checks are
    decision-support signals. Sensitive HR actions require authorized
    human review.

## 16. Engineering practices used

-   Tested the FastAPI health and database-health endpoints.
-   Tested each HR capability through the chatbot.
-   Used actual database-backed tool results rather than inventing
    employee or project records.
-   Kept the original Groq orchestration path as a fallback when the
    LangGraph path raises an exception.
-   Distinguished a successful LangGraph response from a fallback
    response using response metadata.
-   Avoided treating recommendations as completed system actions.
-   Kept API credentials in environment configuration rather than
    embedding them in frontend code.

------------------------------------------------------------------------

**Document purpose:** This file is a development troubleshooting record.
It explains the issues encountered, the changes made, the tests used to
verify those changes, and the limitations that remained at the time of
final testing.
