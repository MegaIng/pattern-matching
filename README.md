# Pattern matching PEP 634

This is a python package implementing pattern-matching similar to what [PEP-634](https://www.python.org/dev/peps/pep-0634/) proposes.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install pattern-matching-pep634.

```bash
pip install pattern-matching-pep634
```

## Usage

There are 4 different implementations of pattern matching in here.

The safest one is this:
```python
from pattern_matching import Matcher

match = Matcher(Click, KeyPress, Quit)

with match(event.get()) as m:
    if m.case('Click(position=(x, y))'):
        handle_click_at(m.x, m.y)
    elif m.case('KeyPress(key_name="Q") | Quit()'):
        m.game.quit()
    elif m.case('KeyPress(key_name="up arrow")'):
        m.game.go_north()
    elif m.case('KeyPress()'):
        pass # Ignore other keystrokes
    elif m.case('other_event'):
        raise ValueError(f"Unrecognized event: {m.other_event}")
```

(This is based on an example in [PEP-636](https://www.python.org/dev/peps/pep-0636/))

Note how you have to specify which names you will be using, and how you always have to use `m.` to access the capture values.
This is the so called `no_magic` implementation. This implementation will work even in Python3.7 and other implementations than CPython that support the same features as 3.7

#### auto_lookup

If you don't want to specify which classes you will be using, but don't want to have the pattern matching messing with the locals, you can use `auto_lookup`

```python
from pattern_matching.auto_lookup import match


with match(event.get()) as m:
    if m.case('Click(position=(x, y))'):
        handle_click_at(m.x, m.y)
    elif m.case('KeyPress(key_name="Q") | Quit()'):
        m.game.quit()
    elif m.case('KeyPress(key_name="up arrow")'):
        m.game.go_north()
    elif m.case('KeyPress()'):
        pass # Ignore other keystrokes
    elif m.case('other_event'):
        raise ValueError(f"Unrecognized event: {m.other_event}")
```

You still have to use `m.`, but at least you don't have to duplicate the class names and carry around a `Matcher` instance.

Note that this might have weird edge cases and fail for some reason sometimes. (Most notably conflict between what you think is visible in a function vs. what really is)

#### injecting

This is for those who don't want to type `m.` everywhere.
```python
from pattern_matching.injecting import match, case


with match(event.get()):
    if case('Click(position=(x, y))'):
        handle_click_at(x, y)
    elif case('KeyPress(key_name="Q") | Quit()'):
        game.quit()
    elif case('KeyPress(key_name="up arrow")'):
        game.go_north()
    elif case('KeyPress()'):
        pass # Ignore other keystrokes
    elif case('other_event'):
        raise ValueError(f"Unrecognized event: {other_event}")
```

This will 'infect' the name space and put the captured names into it. It also does `auto_lookup`.

This is will only work on Python3.9. It might also randomly break with debuggers/coverage/tracing tools.

Note that this heavily suffers from the problem of what locals are defined and what aren't, e.g. the problem of where names are looked up.


#### full_magic

This is the one that is as close as possible to the syntax proposed in PEP-634

```python
from pattern_matching.full_magic import match


with match(event.get()):
    if Click(position=(x, y)):
        handle_click_at(x, y)
    elif KeyPress(key_name="Q") | Quit():
        game.quit()
    elif KeyPress(key_name="up arrow"):
        game.go_north()
    elif KeyPress():
        pass # Ignore other keystrokes
    elif other_event:
        raise ValueError(f"Unrecognized event: {other_event}")
```

(only differences to PEP-634 is `with match` instead of match, `if`/`elif` instead of `case` and `:=` instead of `as`)

This does source-code analysis to figure out what cases to take and which names do bind. This is also Python3.9 only, and might break with any minor release of python. But that is unlikely.

Note: Sometimes, the small amount of optimization that python does can still break this:

```python
from pattern_matching.full_magic import match


with match(n):
    if 1 | 2:
        print("Smaller than three")
    elif 3:
        print("Equal to three")
    elif _:
        print("Bigger than three")
```

Python's peephole optimizer will (normally) correctly figure out that only the first branch can be taken and throw away the rest of the code.
This means that `match` can not correctly jump to the other lines. To circumvent the optimizer, `c@` ('case') can be added to prevent the optimization

```python
from pattern_matching.full_magic import match


with match(n):
    if c@ 1 | 2:
        print("Smaller than three")
    elif c@ 3:
        print("Equal to three")
    elif c@ _:
        print("Bigger than three")
```
 This doesn't have to be done always, but it is a good first attempt if you get weird error messages.


### Guards

Guards are not directly implemented, but are supported via a simple `and` that can be added to a case:

```python
from pattern_matching.injecting import match, case

with match(p):
    if case('(x, y)') and x == y:
        print("X=Y, at", x)
    else:
        print("Not on a diagonal")
```

This works similar for all options

## License
[MIT](https://choosealicense.com/licenses/mit/)