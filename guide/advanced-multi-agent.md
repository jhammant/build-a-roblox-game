# Going faster with several agents (optional)

**You don't need this chapter.** One Claude session, working through the spec piece by piece, builds a family game
perfectly well, and it's what the rest of the guide assumes.

This chapter is for later, when a round of picks produces a lot of features at once and you'd like them built in an
afternoon instead of over several evenings. Gun Flower's biggest update was built this way: 14 builders working in
parallel, each in its own copy of the code, with a merger combining them at the end, and over 300 tests passing at
the merge. It was fast, and it used a lot of compute. Most families won't want that.

## What it costs

Each agent is a separate Claude working at the same time, so a fan-out of 10 builders uses roughly 10 times the plan
allowance of one session, in the same wall-clock time. Check how much of your plan you have left before you try it,
and start with two or three agents, not fourteen.

## What makes it work

Parallel builders only merge cleanly if they agree on the shared pieces before anyone writes code. In Gun Flower
that meant:

1. **Contracts first.** One session updates `ARCHITECTURE.md` with every new remote, Bus event, save section, tag and
   Definitions table the round needs. Nobody starts building until that's done.
2. **An ownership table.** Each builder gets a row: the files it owns, and the other systems' functions it's allowed
   to call. Two builders never edit the same file.
3. **Separate copies of the code.** Each builder works in its own git worktree, so they can't trip over each other.
4. **Tests as the referee.** Each builder writes tests for its own system. The merger runs the whole suite after
   every merge.
5. **One integration playtest at the end**, in Studio, by one session. Parallel builders never start Play, because
   they'd fight over Studio.

## Lessons we learned the hard way

- **Never message an agent while it's running.** In Gun Flower, a message to a running workflow agent didn't reach
  it; it started a duplicate, and two copies then edited the same files. If an agent seems stuck, stop the duplicate
  and wait for the original.
- **Give each long-lived session its own job.** Gun Flower had separate sessions for game code, art, music and the
  logo, each owning its own files, talking through messages. Without that, two sessions editing one file clobber each
  other.
- **Keep one Studio bridge.** Studio only talks to one MCP bridge process at a time. Keep one running for the whole
  session, and let only one agent drive Studio.

## A gentler version for families

If you want to try it, ask Claude for something small:

> Use two agents in parallel for this round: one builds the new bad guys, one builds the reward chest. Write the
> contracts and the ownership table first, give each agent its own worktree, then merge, run the tests and playtest.

Your child might enjoy watching it, too. Gun Flower had a little dashboard that drew each agent as a flower growing
in a garden, so Clara could see the job being split up and put back together. It's a good way to explain what the
"helpers" are doing.
