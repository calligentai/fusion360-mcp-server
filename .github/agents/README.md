# Agent manifests for Copilot Agents

This folder contains example Copilot Agent manifests for BMAD and Fusion360-specific autonomous agents.

How to register an agent

1. Edit the manifest to match your org's model provider and model name. Replace provider/name under the `model` section.
2. Ensure any referenced scripts (entrypoint path) exist and are executable. We include `scripts/agent-runner.sh` as a starter.
3. In the GitHub Copilot Agents UI in VS Code, choose "Add agent" → "From repository" and point to the manifest file path (e.g. `.github/agents/bmad-autonomous-agent.yml`).
4. Grant required permissions when prompted.

Notes
- The manifests use placeholders for BMAD_CLI_PATH and BMAD_API_KEY. Set these as repository or organization secrets or configure the runner environment accordingly.