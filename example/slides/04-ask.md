# Ask

### 9. `[S]` Ask, and argue back

*Summary:* How the AI is used in practice: a first draft and a critic, never the author.

*Text:* 125%

| | |
|---|---|
| **Say what a slide is for** | one line, and it writes the slide to serve it |
| **Ask for changes** | *cut the third bullet, the figure already says it* |
| **Analyse this slide** | it writes what it would change into a box you can edit |
| **Suggest what goes here** | three named moves, with the question each answers |

***

> Strike out what you disagree with. What is left is what runs.

*Delivery note:* Every AI action is a proposal you accept or discard, and one Ctrl-Z puts the slide back. The panels run on your own key under studio.sh, or on a small daily allowance in this demo.

### 10. `[S]` Hand your agent an old deck

*Summary:* A coding agent converts a PowerPoint into a SlAIdy deck by itself; the figure builds up one stage a click.

![[fig-agent-pipeline]]

> Your agent follows `docs/CONVERT.md` and `AGENTS.md`: words as markdown, diagrams redrawn, pictures only where nothing else will do.

*Delivery note:* Give Claude Code, or any coding agent, the link to the repository and the file.
<!-- step -->
ingest.py reads the deck without a model: every slide's text in reading order, its tables, the numbers behind its charts, its pictures and notes.
<!-- step -->
A diagram arrives as a picture of a diagram…
<!-- step -->
…and the agent redraws it as SVG, which you and it can edit afterwards. This is one figure: the bitmap leaves at the click the drawing arrives.
<!-- step -->
shots.mjs photographs every slide at every click, and the agent looks at the pictures before it says it is done.
<!-- step -->
Out comes one HTML file that presents from a link.
