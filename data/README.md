# Data

This folder holds the weights file the app reads at startup.

## Schema

`weights.csv` has exactly four columns:

| Column            | Meaning                                                                 |
|-------------------|-------------------------------------------------------------------------|
| `signal_id`       | Stable opaque ID (e.g. `S001`). Not shown to end users.                 |
| `plain_label`     | Short layman-friendly label rendered in the UI.                         |
| `weight`          | Effect size multiplied by the user's value (0, 1, or 2).                |
| `direction_hint`  | `up` or `down`. Only used to colour contribution chips; never the math. |

## Sample data

`weights.csv` is a **simulated** demo dataset. It is not real biological
data and must not be used to draw real-world conclusions. The labels are
deliberately abstract ("morning energy pattern", "focus marker") so nothing
in this demo can be mistaken for a medical claim.

## Plugging in a real dataset

To swap in a real weights file (for example, a published polygenic risk
score), write a CSV with the same four columns and point
`GENEGAUGE_WEIGHTS_PATH` at it (see `.env.example`). Nothing else in the
app has to change: the loader, validator, and scoring engine will pick it
up as long as the file:

* has all four required columns,
* has unique `signal_id` values,
* has finite numeric `weight` values with magnitude <= 10,
* has `direction_hint` in `{up, down}`,
* contains at most 500 rows.

Invalid rows fail loudly at startup rather than silently producing bad scores.
