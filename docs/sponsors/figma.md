# Figma (Cal Hacks 13.0)

Last updated: 2026-10-24.
Status: target track. [set by Cayden, 2026-10-24]
The longer research is in `CalHacks/ideation/sponsors/figma.md` (outside this repo).
This file holds what Stochastic needs.

## The prizes

- Five prizes at $1,000 each: Best Use Case of Figma, Best Use Case of Figma Agent, Most Creative Use Case of Figma Agent, Best Design, and Most Creative. [verified: Devpost list on 2026-10-15, per `CalHacks/ideation/tracks.md`]
- The guide lists $5K total in Amazon gift cards plus a session with Figma Early Career Recruiting. [self-reported, pre-event guide]
- The prompts are not published in detail.
  Read them on the Live Site. [verified: not found in our notes]
- The Figma workshop was on Friday Oct 23.
  Figma Agent is available through the free Education plan. [verified: pre-event email]

## How Stochastic fits

The fit is real, because the Figma MCP is already in our loop.
We built the design system and four screens in Figma through `use_figma`.
The current UI is the `Hi-fi - v3` page of the team file, https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=141-2, with its `Components` page.
The pitch material is on the `Technologies Used` page. [verified: `../design/README.md`]
The first design system was built in https://www.figma.com/design/KDbPUruO6f5oPLyzyLgUZh. [verified: `../design/README.md`]
It holds one variable collection (`Tokens`), seven text styles, and five components: Actor Chip, Button, Source Chip, Verdict, and Log Row.

Hi-fi v3 has seven screens (Dashboard, upload, Case, Mapping, Log, Agents, and the Review flow), and the console is built from it. [verified: `../design/README.md`]
Show a v3 frame on screen in the pitch.

## What the track needs from us

- The Figma file is the design source for the console, not a one-time export.
- The console screen is built from the Figma frame, with the Figma MCP (`get_design_context`) or Code Connect.
- Figma is on screen in the pitch: the frame, the component set, and one agent-driven edit through `use_figma`.
- Best Design needs polish: one hero screen, plain verdict words, state shown by color plus word plus shape, and a clickable prototype.
- Most Creative needs one idea that is easy to say in a sentence.
  Our candidate: the verdict line changes when the human answers the flag. [inferred]

## What loses (from the research, inferred)

- Static screenshots pasted into Figma.
- A mockup drawn by hand and then called AI.
- Relying on the Figma Agent beta without a fallback to the MCP, because access is plan-gated.
- A generic dashboard with no design judgment.

## Risks and open questions

- Does our team have Figma Agent access?
  If not, only Best Design and Most Creative remain realistic. [inferred]
- Do free seats allow write access through the MCP?
  We have used it in this file, so it works for the current account. [verified: in-session use]
- The exact prompts for the five prizes.
  Read the Live Site and ask a Figma mentor.
- Whether one project can enter Hyphenate, Factory, and Figma together.
  Ask a Cal Hacks organizer.
