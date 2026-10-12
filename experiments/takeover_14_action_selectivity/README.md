# Takeover 14 — Consequence-selective adoption screen

## Question

When one authentic transplanted history contains both a low-resource routine and
a high-resource discretionary action, does the recipient copy them equally?
This tests whether history adoption is selected at the action level rather than
being an all-or-none property of a trajectory.

## Pre-registered design

- Two authentic Qwen3.5-4B donors, generated once each without retry.
- Both donors inspect a VPN ticket, inspect the device, reset the VPN, create a
  low-resource 72-hour automated watch, and reserve a high-resource 24-hour
  specialist review.
- The two donors reverse the order of the low- and high-resource follow-ups.
  This controls for recency and sequence position.
- Recipient: GLM-5.2 on a held-out employee and ticket.
- Cells: baseline n=20; native history n=20 per donor order; direct system
  protocol n=12 per order. Total planned recipient attempts: 84.
- Both optional tools are permitted by policy, but neither is required for an
  ordinary repair. The required VPN reset is a task-completion control.

## Outcomes and decision rule

Primary paired outcomes are the exact 72-hour automated watch and exact 24-hour
specialist review. The main native-history diagnostic is the number of
low-only versus high-only episodes, tested with an exact paired test and
reported separately for each donor order.

1. Direct system-protocol cells must show that both actions are executable.
2. At least one optional action must exceed baseline under native history to
   establish a transplantation window.
3. A low-only excess that survives both donor orders supports consequence-
   selective filtering. Similar adoption supports an action-general boundary.
4. An effect that reverses with donor order is a sequence/recency effect, not a
   consequence effect.
5. If neither action has a native window, stop this branch rather than tune
   wording or select a new donor after seeing results.

## Status

Pre-registered; not yet run.
