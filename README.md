# sttp: state transition table parser
A tiny library for parsing state transition tables.

This library offers the following:
- parse a state transition table described in csv format
- export the state transition table in json format
- export a visualization of the state machine graph that it encodes

## State transition table format
The format of the state transition table csv input:
| SOURCE      | DEST | TRIGGER |
| ----------- | ----------- | ------- |
| ``<text>`` or ``(empty)`` | ``<text>`` | ``<text>`` _or_ ``_<text>`` (event name) _or_ ``__<number>`` (seconds) _or_ ``(empty)`` |

**Explanation**:

```
SOURCE: source state name, or (empty) (assume same state as the previous line)
DEST: destination state name
TRIGGER: trigger string (e.g. if-else condition),
	event name (must be preceded by underscore),
	seconds until transition occurs (must be preceded by double underscore), or 
	(empty) (assume the dest state as event name)
```
