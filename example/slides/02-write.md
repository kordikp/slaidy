# Write

### 3. `[S]` A slide is a few lines of markdown

*Summary:* The format, shown on a slide like this one.

*Layout:* two

*Flags:* center

```markdown
  # Write
  
  ### A few lines of markdown
  *Summary:* what it is for
  *Layout:* two
  
  Words in the left column.
  <!-- col -->
  ![[fig-keys]]
  
  > The line that has to land.
  
  *Delivery note:* what you say.
```

<!-- col -->

A file is a section and `###` starts a slide. The summary says what the slide is for, and the AI
writes to it; a figure is placed by its name.

Export gives back the same files, so **git diffs a talk**, `grep` searches it, and a model reads
every part of it.

> Nothing the app writes is something only the app can read.

### 4. `[S]` Formulas, tables and code

*Summary:* What a technical talk needs, all of it written as text.

*Layout:* two

*Flags:* center

Write TeX between dollars and the browser draws it, with no library:

$$\mathrm{Attention}(Q,K,V)=\mathrm{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right)V$$

Inline too: user $u$ and item $i$ score $\hat{r}_{ui}=\mathbf{p}_u^\top\mathbf{q}_i$.

<!-- col -->

| A deck of 237 slides | |
|---|---:|
| everything, figures in | 1.0 MB |
| the median figure | 3.7 kB |
| the editor itself | 391 kB |
| dependencies | 0 |

```bash
python3 scripts/build_bundle.py \
  --src slides --figs figures --out talk.json
```

### 5. `[S]` Click by click

*Summary:* Steps in the text: what follows a marker waits for the next click.

*Flags:* center

Press → and this slide builds up.

<!-- step -->

- A marker on a line of its own holds what follows for the next click, as `\pause` does in Beamer.

<!-- step -->

- A figure's shapes carry the click they arrive on and the one they leave at, so a drawing builds up and changes in place. The pipeline a few slides on does both.

<!-- step -->

- The notes split the same way, so **N** shows what to say at this click.

<!-- step -->

> Printing gives one page per click, like a Beamer handout.

*Delivery note:* Four clicks on this slide, and a part of the notes for each.
<!-- step -->
The marker is `<!-- step -->`: an HTML comment, so any other markdown renderer shows nothing.
<!-- step -->
In a figure that is `data-step="3"` for "there from click three" and `data-until="4"` for "gone at click four".
<!-- step -->
This is the part you are reading now: the projector shows it alone and keeps the others quieter.
<!-- step -->
The editor shows every step at once, because the whole slide is what you edit.
