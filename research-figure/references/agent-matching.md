# Agent matching and scope boundaries

The SKILL.md metadata is the minimal discovery contract. Prioritize actual requested artifact over topic words; a vague use of "paper", "model" or "figure" alone does not necessarily trigger RFS.

**Match:** method/overview/mechanism figure, precision scientific TikZ/LaTeX formula-timing or reproducible vector architecture figures, creative figure prompt for a scientific paper, figure generation from experimental CSV, comparison/refinement of candidate scientific figure images, editable reconstruction of an approved scientific diagram, scientific figure audit. Do not trigger this skill for ordinary LaTeX document typesetting or explanations that only mention TikZ without requesting a figure. An explicit `--engine tikz` stays a local opt-in and must not change the default creative-route selection.

**Do not match:** explain remote-sensing concepts without creating a figure, train/tune ML models without figure deliverables, write paper sections, make social posters/general slides, business dashboards, casual photos, or a user explicitly choosing another Skill such as `$paper-fig` for a single operation.

The optional `agents/openai.yaml` only supplies host-facing metadata. It is **not** a portable override for the Agent Skills open frontmatter format.

`tests/agent_matching_cases.json` contains user-utterance fixture expectations for real host LLM selection tests. The included unittest verifies only fixture shape and boundary coverage; it does not measure actual triggering accuracy. Test true host auto-selection across positive, negative and competing-Skill cases before publishing a claim of high precision/recall.
