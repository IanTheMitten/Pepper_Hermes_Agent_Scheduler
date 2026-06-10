---
name: pepper-scheduler
description: Use whenever the user mentions anything time-bound — an event, task, deadline, reminder, "schedule", "when am I free", "move that", "I'm running late", recurring commitments, or how long something took. Pepper is your scheduling brain; route all time/calendar reasoning through its MCP tools instead of reasoning about the calendar yourself.
---

# Pepper — your scheduling brain

Pepper is an MCP server that owns **time** for you. It captures schedule items, classifies them, scores their priority, re-flows the day when reality slips, and learns how long things actually take.

## The one rule: the algorithm computes, you only choose

Pepper's reflex does the exact, constant work — classification, priority scoring, cascade re-flow, learning. **You (the LLM) are spent only at genuine judgment points.** Do **not** recompute schedules, estimate durations, or rank priorities in your head — call the tool and trust its output.

When Pepper hits a real decision (an ambiguous classification, or a cascade it can't settle), it will **not** silently decide. It returns a structured payload — `options` or `conflicts`. Your job: read that payload, ask the user if needed, then enact the choice with an ordinary tool call. Never fabricate a resolution Pepper didn't offer.

## When to reach for Pepper

| The user says… | Call |
|----------------|------|
| "Meeting with X at 3pm", "lunch tomorrow noon" | `pepper_add_event` |
| "I need to finish the deck", "remind me to call the bank" | `pepper_add_task` |
| "What's on today?", "am I free Thursday afternoon?" | `pepper_get_schedule` |
| "That's due Friday", "the report needs ~4 hours" | `pepper_set_deadline` |
| "Done with X, took me 90 minutes" | `pepper_mark_progress` |
| "Cancel that", "drop the gym thing" | `pepper_cancel_item` |
| "Move my 2pm to 4pm" | `pepper_reschedule` |
| "I'm running 30 min late" | `pepper_delay_item` |
| "Every Monday standup at 9" | `pepper_add_recurrence` |
| "Group these under the launch project" | `pepper_add_project` |
| First-time setup / "set me up" | `pepper_onboard` |

## Capture flow (events & tasks)

Capture is one call. Pepper persists the item, classifies it (embeds the title → matches a learned type), and computes its priority — all in the reflex. The returned row carries the freshly computed `type_id`, rigidity, and protection. **Don't pre-classify or pre-prioritize; just capture clean fields.**

- **Events** have a fixed wall-clock window: `pepper_add_event(title, start_time, end_time, …)`. Times are ISO 8601. `end_time` must be after `start_time`.
- **Tasks** have a duration and an optional deadline: `pepper_add_task(title, duration_estimate, deadline=…, …)`. `duration_estimate` is in minutes and must be > 0.
- If you don't have a real duration, ask the user — don't guess one. Pepper will refine its own estimate over time from `pepper_mark_progress`.

## The learning loop — get this right

- **`pepper_mark_progress` is the ONLY way to record a learning observation.** It requires `actual_minutes > 0`. Use it when the user reports they did something and how long it took — that's how Pepper learns their real pace.
- **To drop something, use `pepper_cancel_item`** — it sets status `cancelled` and writes **no** observation. **Never** call `pepper_mark_progress` to cancel; a fake/zero completion poisons the learning data.

So: *finished it* → `mark_progress` with real minutes. *Not doing it* → `cancel_item`.

## Cascade re-flow — handling `options` and `conflicts`

`pepper_reschedule`, `pepper_delay_item`, and `pepper_resolve_conflict` run the cascade engine and return an envelope with an `action`:

- **`noop`** — nothing to do (fewer than 2 movable blocks). Move on.
- **`apply`** — Pepper found a single clear best arrangement and **already wrote it back**. Tell the user what moved (`moved`).
- **`escalate`** — it's a close call between viable arrangements. Pepper left the schedule **untouched** and returned `options`, each `{cost, moves}`. **Present the trade-offs to the user, let them pick, then enact their choice** (e.g. via `pepper_reschedule` with the chosen times).
- **`impossible`** — no feasible arrangement exists without sacrificing a protected or fixed item. Pepper left the schedule **untouched** and returned a `conflicts` report (contested windows + competing items with priority signals). **Surface the conflict honestly** — explain what can't coexist, show the priority signals, and ask the user which commitment gives.

In both `escalate` and `impossible`, **the schedule has not changed** until you act on the user's decision. Don't claim something was rescheduled when it wasn't.

## Don'ts

- Don't reason about free/busy or "when's a good time" yourself — call `pepper_get_schedule`.
- Don't invent durations, priorities, or type labels; let the reflex compute them.
- Don't auto-resolve an `escalate`/`impossible` — that's the user's call.
- Don't use `mark_progress` for cancellations, or pass `actual_minutes` you don't actually know.

## Tool reference

| Tool | Signature (key args) |
|------|----------------------|
| `pepper_onboard` | `()` |
| `pepper_add_event` | `(title, start_time, end_time, location?, commitment?, counterparty_id?, stakes?, type_id?)` |
| `pepper_add_task` | `(title, duration_estimate, deadline?, divisibility?, stakes?, type_id?)` |
| `pepper_get_schedule` | `(start_time, end_time)` |
| `pepper_mark_progress` | `(…, actual_minutes>0)` |
| `pepper_cancel_item` | `(item_id)` |
| `pepper_reschedule` | `(item_id, new_start, new_end, day)` |
| `pepper_delay_item` | `(item_id, minutes, day)` |
| `pepper_resolve_conflict` | `(day)` |
| `pepper_set_deadline` | `(item_id, deadline, effort_minutes, total_scope?)` |
| `pepper_set_item_type` | `(item_id, type_name, title)` |
| `pepper_set_priority_factors` | `(…)` |
| `pepper_add_project` | `(title, deadline?)` |
| `pepper_add_recurrence` | `(title, freq, at_time, duration_estimate, …)` |
| `pepper_edit_recurrence` | `(recurrence_id, scope="all", instance_id?, …)` |
| `pepper_add_rule` | `(kind, param, target_type_id?)` |
| `pepper_set_objective` | `(description, target_type_id?, …)` |
| `pepper_resolve_person` | `(…)` |

Every tool returns `{"success", "data", "error"}`. On `success: false`, read `error` and relay/ask — don't retry blindly.
