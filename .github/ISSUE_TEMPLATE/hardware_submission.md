---
name: Hardware Wall Submission
about: Submit your machine's benchmark run and budget card to the OpenPhysicalAI Hardware Wall
title: '[HARDWARE] '
labels: hardware-wall
assignees: ''
---

### Device Profile (`opai doctor`)
Paste the raw JSON from running `opai doctor` on your system:
```json
// Paste opai doctor output here
```

### Benchmark Run (`opai run` budget card)
Paste the Budget Card markdown produced by running the benchmark:
```markdown
// Paste Budget Card here
```

### Reproduce Command
```bash
// Paste reproduce command here
```

### Verification Checklist
- [ ] Ran without modifying simulator physics or verifier logic
- [ ] Reported baseline VRAM and peak VRAM truthfully
- [ ] N >= 50 episodes included
