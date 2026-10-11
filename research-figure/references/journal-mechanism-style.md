# Journal-style mechanism figures — RFS default

## Scope and precedence

For standalone academic figures, the default is **one scientific question per figure**. When an overall architecture and two important internal mechanisms all need detail, create **three independently captioned images**, not one three-panel infographic. Explicit user requirements and the target journal's instructions take precedence.

Inside each standalone image:
- **No large title, subtitle, Figure number, (a)/(b)/(c) panel marker, or numbered 1–6 stage headings.** Put figure titles and explanations in the manuscript caption. This does not prohibit functional labels beside actual modules.
- **No decorative stage cards, contribution banners, or bottom summary timeline.** Boundaries should distinguish actual computational groups, loops, modalities or stages only when scientifically necessary.
- **Dense but ordered:** prioritize process details and readable routing; eliminate unjustified whitespace without cramming tiny type or long prose.
- **Every term and arrow needs a source:** modules, dimensions, tensor operations, supervision routes, training vs inference behavior and equations must be supported by manuscript methods, code, or a clearly marked hypothesis.
- **Semantic color, not decoration:** use restrained colors consistently for modalities and operations; arrows and symbols must remain distinguishable in grayscale.

The (a)/(b)/(c) convention is legitimate and often required for one **combined multipanel figure**; it is simply unnecessary for three separately submitted figures. Nature advises logical grouping and keeping the figure legend outside the graphic. Nature Synthesis advises against both huge white gaps and overcrowding.

## MRLQ conceptual example — not verified architecture

Separate deliverables, each with its own FigureSpec and caption:
1. **Overall network:** Optical/SAR input -> modality-specific encoding -> verified shared and label interaction -> router -> evidential/prediction path. Show each operation once; avoid detailed derivations.
2. **Label-wise Router:** exact origin of label queries and Key/Value -> label feature extraction -> router scores and normalization -> optical/SAR weighted aggregation -> per-label representation. Only render actual formulas and shapes from verified source.
3. **Evidential Fusion:** evidence generation for each source -> documented fusion operator -> per-label confidence, prediction and uncertainty. Do not insert an invented MLP or arbitrarily choose Dirichlet or Dempster–Shafer.

**Critical mathematical safeguard:** A per-sample multi-class Dirichlet over mutually exclusive K categories is not automatically valid for multi-label independent binary decisions. Generic argmax-over-labels and K/sum(alpha) uncertainty equations must not be copied into MRLQ until the actual model formulation is verified.

## Art direction for generative models

Make one **standalone, titleless, captionless, compact publication figure**. Start the computational story near the canvas edges. Use connected scientific objects, precision arrows and essential math, not a poster grid. Suppress decorative title ribbons, stage numbers, panel letters, promotional claim badges, and filler icons. Make the flow legible at actual journal column width. If the user asks for one multi-panel composite, restore the required panel letters rather than applying this rule blindly.

## Acceptance order

1. Scientific correctness: source-grounded terminology, topology, direction, formulas, task type and data.
2. Figure framing: no in-image title/subtitle, stage numbers, unsolicited panel letters or gratuitous colored cards.
3. Mechanism clarity: visible inputs, transformations, weights, operators, merges and outputs.
4. Publication readability: dense but unoccluded, consistent typesetting, grayscale and column-width legibility.
5. Reconstruction: verify original image plus FigureSpec plus image-anchored notes; independently inspect real PPTX/draw.io objects and render.

## Peer-reviewed figure evidence / venue guidance

- Nature figure formatting: https://www.nature.com/nature/for-authors/formatting-guide
- Nature initial submission: https://www.nature.com/nature/for-authors/initial-submission
- Nature Synthesis, Figuring it out: https://www.nature.com/articles/s44160-022-00067-8
- Nature Communications 2025, NuFold Figure 1 (example of a valid *combined* multipanel figure): https://www.nature.com/articles/s41467-025-56261-7
- CVPR 2024, AllSpark Figures 2–4 (actual attention and training information flows): https://openaccess.thecvf.com/content/CVPR2024/papers/Wang_AllSpark_Reborn_Labeled_Features_from_Unlabeled_in_Transformer_for_Semi-Supervised_CVPR_2024_paper.pdf
- CVPR 2022, Partial Class Activation Attention Figure 2 (overall network and attention detail): https://openaccess.thecvf.com/content/CVPR2022/papers/Liu_Partial_Class_Activation_Attention_for_Semantic_Segmentation_CVPR_2022_paper.pdf
- IEEE Author Center graphics guidance: https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/
- NeurIPS 2018 Evidential Deep Learning (multiclass mathematical scope): https://arxiv.org/abs/1806.01768
- IEEE TPAMI Trusted Multi-View Classification with Dynamic Evidential Fusion: https://pubmed.ncbi.nlm.nih.gov/35503823/

These papers and their graphics are **references, not template assets for redistribution**. Do not copy their figure images into this public Skill repository.