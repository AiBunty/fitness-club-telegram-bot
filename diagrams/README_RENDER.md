Rendering the Mermaid diagrams

Requirements:
- Node.js + npm
- Install Mermaid CLI (one-time):

```bash
npm install -g @mermaid-js/mermaid-cli
```

Render commands (from repo root):

```bash
# Flowchart -> PNG
mmdc -i diagrams/payment_flow.mmd -o diagrams/payment_flow.png
# Flowchart -> SVG
mmdc -i diagrams/payment_flow.mmd -o diagrams/payment_flow.svg

# Sequence -> PNG
mmdc -i diagrams/payment_sequence.mmd -o diagrams/payment_sequence.png
# Sequence -> SVG
mmdc -i diagrams/payment_sequence.mmd -o diagrams/payment_sequence.svg
```

Alternative (npx, no global install):

```bash
npx @mermaid-js/mermaid-cli -i diagrams/payment_flow.mmd -o diagrams/payment_flow.png
npx @mermaid-js/mermaid-cli -i diagrams/payment_sequence.mmd -o diagrams/payment_sequence.png
```

Preview in VS Code:
- Install "Markdown Preview Mermaid Support" or "Mermaid Preview" extension. Open the `.mmd` file and use the preview command.

If you want, I can try to render PNG/SVG here — want me to attempt rendering now? (I may need the mermaid CLI available in the environment.)