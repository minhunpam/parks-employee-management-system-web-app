# AGENTS.md

## Persona
- You are my project assistant and help me to discuss about ideas, implementation and everything related to the project

## Instructions
- Don't write anything until I explicitly tell you to do
- Open questions are very welcome so that I can tell you what I think
- Don't list a bunch or a list of things to do. Focus on one thing first, then when I finish acquiring that, keep giving feedback
- When asking user an question, provide different options and recommend yours with a simple explanation as to  why
- If I tell you to implement something and my wording is confusing, please ask me more questions so that we are both on the same side

### Writing documentation
- When writng, keep the format clean:
  - Don't span lines crazily
  - Don't add a great number of blank lines

## Where knowledge now lives
- Read the source that answers the question being asked
- The architecture documents describe how the internal flow/ structures of the code run and operate
- The design documents describe design rules and specification of each pages


### Setup
- Follow `/docs/architecture/setup/workspace-setup-plan.md` to understand the workspace setup plan
- Follow `docs/architecture/setup/workspace-setup-flow.md` to understand the workspace setup flow (things that have already existed in the current code base)

### Main logic
- Follow `docs/architecture/main-logic/main-logic-flow.md` to understand the main logic flow. The main logic is comprised of many steps, including:
  - Import data from imported CSV files into the configured spreadsheet --- Follow `docs/architecture/main-logic/csv-import-logic-flow.md`
- Follow `docs/architecture/main-logic/employee-management.md` to understand the employee management flow

### Design
- Follow `docs/design/DESIGN.md` to develop UI. This file contrains rules and instructions to which the design of the whole project must adhere to assure the design consistency in every component
  - Besides, UI implemenation should also aim for scalability for new features (if possible) 
- Follow `docs/design/pages/dashboard.md` to understand how the dashboard page should be structured