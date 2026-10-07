"""RobotClient - command client for the lab robots.

Usage:
    python client.py eric:walk deby:firmware_update chuck:get_status
"""

import re
import sys
import threading
import time

import executor


# ---------------------------------------------------------------------------
# Logging framework
# ---------------------------------------------------------------------------

class Logger(object):
    """Our own logger, the built in logging module is too complicated."""

    _instance = None

    LEVEL_INFO = 1
    LEVEL_ERROR = 2

    def __new__(cls):
        if Logger._instance is None:
            Logger._instance = super(Logger, cls).__new__(cls)
        return Logger._instance

    def log(self, level, message):
        t = time.localtime()
        stamp = str(t.tm_hour) + ":" + str(t.tm_min) + ":" + str(t.tm_sec)
        if level == Logger.LEVEL_INFO:
            print("[" + stamp + "] " + "INFO" + " " + str(message))
        elif level == Logger.LEVEL_ERROR:
            print("[" + stamp + "] " + "ERROR" + " " + str(message))
        else:
            # unknown level, log it as info anyway
            print("[" + stamp + "] " + "INFO" + " " + str(message))


class LoggableEntity(object):
    """Anything in the system that wants to log should inherit from this."""

    def __init__(self):
        self.logger = Logger()

    def log_info(self, message):
        self.logger.log(Logger.LEVEL_INFO, message)

    def log_error(self, message):
        self.logger.log(Logger.LEVEL_ERROR, message)


# ---------------------------------------------------------------------------
# Base entity layer
# ---------------------------------------------------------------------------

class BaseEntity(LoggableEntity):
    """Base class for every named entity (robots, commands, ...)."""

    def __init__(self, name):
        super(BaseEntity, self).__init__()
        self.name = name

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name


# ---------------------------------------------------------------------------
# Robots
# ---------------------------------------------------------------------------

class BaseRobot(BaseEntity):
    """Base class for all robots. Subclass this to add a robot to the fleet."""

    ip = None

    def __init__(self, name):
        super(BaseRobot, self).__init__(name)

    def get_ip(self):
        return self.ip

    def set_ip(self, ip):
        self.ip = ip


class EricRobot(BaseRobot):
    ip = "192.168.10.11"

    def __init__(self):
        super(EricRobot, self).__init__("eric")


class DebyRobot(BaseRobot):
    ip = "192.168.10.24"

    def __init__(self):
        super(DebyRobot, self).__init__("deby")


class ChuckRobot(BaseRobot):
    ip = "192.168.10.7"

    def __init__(self):
        super(ChuckRobot, self).__init__("chuck")


class RobotFactory(object):
    """Singleton factory that creates robot objects by name."""

    _instance = None

    def __new__(cls):
        if RobotFactory._instance is None:
            RobotFactory._instance = super(RobotFactory, cls).__new__(cls)
        return RobotFactory._instance

    def create_robot(self, robot_name):
        if robot_name == "eric":
            return EricRobot()
        elif robot_name == "deby":
            return DebyRobot()
        elif robot_name == "chuck":
            return ChuckRobot()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

class BaseCommand(BaseEntity):
    """Base class for all commands. Subclass this to add a command."""

    def __init__(self, name):
        super(BaseCommand, self).__init__(name)

    def to_command_string(self):
        return self.get_name()


class GetStatusCommand(BaseCommand):
    def __init__(self):
        super(GetStatusCommand, self).__init__("get_status")


class MoveArmCommand(BaseCommand):
    def __init__(self):
        super(MoveArmCommand, self).__init__("move_arm")


class WalkCommand(BaseCommand):
    def __init__(self):
        super(WalkCommand, self).__init__("walk")


class FirmwareUpdateCommand(BaseCommand):
    def __init__(self):
        super(FirmwareUpdateCommand, self).__init__("firmware_update")


class CommandFactory(object):
    """Singleton factory that creates command objects by name."""

    _instance = None

    def __new__(cls):
        if CommandFactory._instance is None:
            CommandFactory._instance = super(CommandFactory, cls).__new__(cls)
        return CommandFactory._instance

    def create_command(self, command_name):
        if command_name == "get_status":
            return GetStatusCommand()
        elif command_name == "move_arm":
            return MoveArmCommand()
        elif command_name == "walk":
            return WalkCommand()
        elif command_name == "firmware_update":
            return FirmwareUpdateCommand()
        else:
            # future proofing: new commands will still work without a class
            return BaseCommand(command_name)


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------

class CommandQueue(list):
    """A queue of (robot, command) tuples. Newest command of a type wins."""

    def add_command(self, robot, command):
        # Phase 4: drop older commands of the same type, only newest runs
        for queued_item in self:
            if queued_item[1].get_name() == command.get_name():
                self.remove(queued_item)
        self.append((robot, command))

    def get_next_command(self):
        return self.pop(0)

    def has_commands(self):
        if len(self) > 0:
            return True
        else:
            return False


# ---------------------------------------------------------------------------
# Retry support
# ---------------------------------------------------------------------------

class RetryingExecutorMixin(object):
    """Mixin that adds retry capability. Phase 3: retry up to 3 times."""

    MAX_RETRIES = 3

    def execute_with_retry(self, ip, command_string):
        retries = 0
        while retries < self.MAX_RETRIES - 1:
            try:
                result = executor.execute(ip, command_string)
                return result
            except:
                retries = retries + 1
                self.log_error("attempt " + str(retries) + " failed for " + command_string)
        return "ERROR: " + command_string + " failed"


# ---------------------------------------------------------------------------
# The client
# ---------------------------------------------------------------------------

class RobotClient(threading.Thread, RetryingExecutorMixin, LoggableEntity):
    """The client the backend team uses to command the fleet.

    It is a thread that works through the command queue in the background.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        LoggableEntity.__init__(self)
        self.queue = CommandQueue()
        self.results = {}
        self.robot_factory = RobotFactory()
        self.command_factory = CommandFactory()

    def send_command(self, robot_name, command_name):
        robot = self.robot_factory.create_robot(robot_name)
        command = self.command_factory.create_command(command_name)
        self.queue.add_command(robot, command)
        self.log_info("queued " + command.get_name() + " for " + robot.get_name())

    def run(self):
        # main worker loop, processes the queue one command at a time
        while True:
            if self.queue.has_commands() == False:
                time.sleep(1)
                continue
            robot, command = self.queue.get_next_command()
            self.log_info("sending " + command.get_name() + " to " + robot.get_name())
            result = self.execute_with_retry(robot.get_ip(), command.to_command_string())
            self.results[robot.get_name()] = result


# ---------------------------------------------------------------------------
# Command line handling
# ---------------------------------------------------------------------------

def parse_argument_into_robot_name_and_command_name(argument):
    matcher = re.compile("^([a-zA-Z]+)\\:([a-zA-Z_]+)$")
    match_result = matcher.match(argument)
    robot_name = match_result.group(1)
    command_name = match_result.group(2)
    return (robot_name, command_name)


def main():
    client = RobotClient()
    client.daemon = True
    client.start()

    for argument in sys.argv[1:]:
        parsed = parse_argument_into_robot_name_and_command_name(argument)
        client.send_command(parsed[0], parsed[1])

    # wait for all the commands to finish. firmware_update is the longest
    # command so 20 seconds should be more than enough for everything.
    time.sleep(20)

    print("")
    print("==== RESULTS ====")
    for robot_name in client.results:
        print(robot_name + " -> " + client.results[robot_name])


if __name__ == "__main__":
    main()
