# Trigger / delegation regression examples

| User intent | Expected entry and internal route |
| --- | --- |
| 用 research-figure 根据模型代码画机制图 | RFS loads design-core + local layout-library without requiring upstream names |
| Give me a precise TikZ diagram | RFS vector route, no forced image call |
| Plot these measured CSV values | Source-data plot; no synthesized values |
| Convert this approved image to editable PPTX | Three-source reconstruction; no new concept design |
| Explain what attention means | Not a scientific-figure request by itself |
| Update the reference library from upstream | check → diff/license review → pull → verify → tests |

Programmatic route tests do not measure real host LLM invocation precision.
The host must actually load the complete installed Skill and expose required tools.
The deterministic tests explicitly check internal modes, old aliases, absent
runtime, invalid override, permission gates, and prompt-vs-image distinctions.
