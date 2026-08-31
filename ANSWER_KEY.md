# Interviewer Answer Key — client.py (do not share)

Legend: **[MUST]** = required to pass at this level; unmarked = strengthens the signal but forgivable to miss.

## Level 1 — Must-find (deal-breakers)

*Must-haves: all four — missing any of these is a red flag.*

1. **[MUST] No real parallelism** — a single worker thread serves the whole fleet, so deby's firmware_update blocks chuck's instant get_status; Phase 5 is effectively unimplemented.
2. **[MUST] Thread-unsafe queue** — `CommandQueue` is a plain `list` shared between the main and worker threads with no lock, so dedup/append can race with `pop(0)`.
3. **[MUST] Broken error handling in retry** — bare `except:` swallows everything (even Ctrl-C and permanent errors), the loop only tries **2** times instead of 3, and failure is reported as an `"ERROR: ..."` string indistinguishable from a real robot reply.
4. **[MUST] Inheritance abuse** — `RobotClient(Thread, RetryMixin, LoggableEntity)` plus a subclass per robot and per command that only set two data fields; all should be composition/plain data.

## Level 2 — Medium (expected from a solid candidate)

*Must-haves: #1 and #3 — the spec violation and the fake wait; #2 and #4 are strong bonuses.*

1. **[MUST] Dedup ignores the robot** — Phase 4 matches on command type only, so eric's new `walk` silently deletes deby's queued `walk`.
2. **Mutating while iterating** — `for item in self: self.remove(item)` skips elements, so duplicates can survive dedup.
3. **[MUST] `time.sleep(20)` as completion-wait** — main guesses the duration instead of joining, and the daemon thread means unfinished commands are silently killed at exit (real firmware_update takes minutes → results vanish).
4. **Unvalidated input crashes late** — unknown robot returns `None` and blows up *after* queuing, unknown commands are wrapped and sent (then pointlessly retried), and a malformed arg like `eric_walk` crashes the regex parser with `AttributeError`.

## Level 3 — Minor (nice to catch)

*Must-haves: none — these differentiate good from great; expect a strong candidate to surface 2–3.*

1. **Results overwrite** — `results` is keyed by robot name, so a second command to the same robot erases the first result.
2. **Busy polling** — worker loops with `sleep(1)` instead of a blocking `Queue.get()`, adding latency.
3. **Singleton boilerplate** — hand-rolled `__new__` singletons on Logger and both factories, none of which needs to exist.
4. **Reinvented logging** — custom Logger instead of stdlib `logging`, with string-concatenated, unpadded timestamps (`15:44:2`).
5. **No timeout** — a robot that never replies wedges the worker forever.
6. **In-flight command can't be deduped** — a stale command already popped still runs even if a newer one arrives (good discussion point).
7. **Java-in-Python noise** — getters/setters, `== False`, `if len > 0: return True else: return False`, `retries = retries + 1`, `pop(0)` O(n), 47-char function name + regex to split on a colon.

## Strong-answer shape

Per-robot `queue.Queue` + worker (or ThreadPoolExecutor/asyncio with per-robot serialization); dedup keyed on (robot, type) under the queue lock; `for attempt in range(3)` catching only `ConnectionError`, re-raising the last; results as futures/records; `Robot(name, ip)` data + dict, commands as constants; stdlib logging; main joins on completion.
