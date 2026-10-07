# Robot Command Client

Our backend team sends commands to the robots in the lab (eric, deby, chuck).
This client is the one place that knows the robot API and makes sending
commands easy, reliable, and efficient.

## Requirements implemented

1. Send a command to any robot by name.
2. Accept several commands at once; a robot only accepts one command at a time.
3. Retry a command up to 3 times before reporting failure (flaky network).
4. When a command is submitted for a robot, any command of the same type
   already queued for that robot is dropped — only the newest one runs.
5. Different robots can be commanded at the same time.

## Usage

```
python3 client.py eric:walk deby:firmware_update chuck:get_status
```

`executor.py` is a simulation of the internal executor package
(`executor.execute(ip, command_string) -> str`) and is not part of this
change — review `client.py` only.
