# 2. Dream it (kid leads, parent writes it down)

**Who leads:** your child. You ask and write; Claude turns it into a spec.

**You'll end up with:** `SPEC.md` in your game folder: the game, described in your child's own words, plus a list of
things still to choose.

**Time:** 20 to 30 minutes with your child, then a few minutes with Claude.

## Why their words matter

A spec written in a child's words is a better spec than a tidy grown-up one, because it keeps what they actually
care about. Clara H. said Gun Flower's monsters should be "scary, not too much, top hats on them". Every later
decision about the monsters (eyeless faces, jagged cartoon teeth, a magician's top hat on every one) came from those
seven words. A grown-up summary ("moderately threatening enemies") would have lost the top hats.

So your job here is to be a scribe, not an editor. Write down what they say, even when it's odd. *Especially* when
it's odd.

## Three ways to capture it

1. **Talk, then hand Claude the notes.** Chat with your child (in the car, at dinner, at bedtime) and jot down what
   they say. Then give Claude your notes.
2. **Record a voice memo** on your phone, then give Claude the transcript. (Most phones can transcribe; otherwise read
   it out yourself.) Keep the recording itself on your own device. It doesn't go in the game folder.
3. **Let `/dream` interview them.** Start Claude Code in the game folder, type `/dream`, and read Claude's questions
   to your child. Type their answers word for word.

Drawings are welcome. Take a photo of the drawing and give it to Claude in the same session. Keep the photo on your
computer; don't commit it to the game folder if your child's name or handwriting is on it.

## Questions to ask your child

Start wide, then get specific. You won't need all of these.

**The big idea**

- "What's your game about?"
- "If your friend played it for one minute, what would they do?"
- "What's the funniest thing that could happen in it?"

**The loop** (the thing you do over and over)

- "What do you collect?"
- "What do you make with it? Where do you make it?"
- "What do you use it on? What happens then?"

**The world**

- "Where does it happen? What colour is it?"
- "Is there anywhere secret or special?"

**The characters**

- "Who are you in the game?"
- "Who are the bad guys? Are they funny, or scary, or both? How scary is OK?"
- "What happens when you beat one?"

**The feelings**

- "What should it feel like? Exciting, cosy, silly, spooky?"
- "What would make you want to play it again tomorrow?"

If they get stuck, offer two silly options ("Is it more like a bouncy castle or a haunted house?"). Don't offer
your own idea as the answer.

## Running `/dream`

In the game folder:

```bash
claude
```

Then type:

> /dream

Claude asks you whether you're bringing notes, a transcript or doing a live interview, then:

- writes `SPEC.md` with your child's phrases kept as quotes,
- describes the **core loop** in one line (for example: collect → make → use → reward → explore further),
- fills small gaps with sensible defaults and **marks them as defaults**, so you can check them,
- lists everything that's still to choose under **To pick**, which become the boards in [phase 3](03-pick-it.md).

## Check it with your child

Ask Claude to read `SPEC.md` back in plain words, and read it to your child. Ask:

- "Is that your game?"
- "Is anything wrong, or missing?"

Change it until they say yes. That "yes" is the point of this phase.

## What a good spec looks like

From Gun Flower (the full version is in [`examples/gun-flower/`](../examples/gun-flower/)):

> Explore → find flowers → collect flowers → take them to the magical stream → create flower guns → fight monsters →
> monsters become flowers → collect better flowers → create more powerful guns → explore further.
>
> Clara's key idea: **they have no eyes.**

One loop, a few vivid details in the child's words, and a clear list of what's still open.

## Tips

- **Don't fix it.** If the game sounds impossible, keep it. Claude will build a simple first version and say what's
  coming later.
- **Write down "why" when they give one.** "The monsters wear top hats because they're magicians" helps every later
  decision.
- **Keep scary in check gently.** If they want scary, ask "scary like a ghost train, or scary like a nightmare?" and
  write down their answer. Kids usually choose ghost train.
- **Stop while it's fun.** You can add to `SPEC.md` any time.

**Next:** [3. Pick it](03-pick-it.md).
