#!/usr/bin/python3

import shutil
from configparser import RawConfigParser
from math import pow
from os import listdir, remove, path
from sys import argv
from typing import Callable
import re


class Command:
    def __init__(self, long: str, short: str, description: str, fun: Callable):
        self.description = description
        self.fun = fun
        self.short = short
        self.long = long


# noinspection PyTypeChecker
help_command = Command("help", "h", "Show Help", None)

config = RawConfigParser()
config.read("steam_storage.ini")

if "Libraries" not in config:
    print("No Libraries specified in steam_storage.ini")

libraries = config["Libraries"]
for i in libraries:
    if "~" in libraries[i]:
        libraries[i] = path.expanduser(libraries[i])


class Game:
    def __init__(self, lib, acf) -> None:
        self.acf = acf
        self.lib = lib
        self.contents = open(libraries[lib] + acf).read().split("\n")

    def get(self, attrib):
        for line in self.contents:
            search = re.search("\t+\"" + attrib + "\"\t+\"(.+)\"", line)
            if search:
                return search[1]
    
    def get_path(self):
        return path.join(libraries[self.lib], "common", self.get("installdir"))

    def get_acf(self):
        return path.join(libraries[self.lib], self.acf)

    def get_size(self):
        bytes = int(self.get("SizeOnDisk"))
        gb = (bytes / pow(1024, 3))
        return round(gb, 2)

    def __get_target_path(self, new_lib):
        return path.join(libraries[new_lib], "common", self.get("installdir"))
    
    def __get_target_acf(self, new_lib):
        return path.join(libraries[new_lib], self.acf)
    
    def move(self, new_lib):
        shutil.move(self.get_acf(), self.__get_target_acf(new_lib))
        shutil.move(self.get_path(), self.__get_target_path(new_lib))

    def __repr__(self):
        return "Game: " + self.acf

try:
    compat = config["CompatData"]
except KeyError:
    compat = []

reserve = float(config["Settings"]["Reserve"])

acf_files = [] # list of steam .acf files 
for library in libraries: # add .acf files from each library to acf_files
    _acf_files = [x for x in listdir(libraries[library]) if x.endswith(".acf")]
    for file in _acf_files:
        acf_files.append(Game(library, file))


def list_games(params=None):
    if not params: # if no library parameter supplied check all
        libraries_to_check = [x for x in libraries]
    else:
        libraries_to_check = params # check libraries in params

    print("Libraries")
    for i in libraries_to_check:
        _, _, free = shutil.disk_usage(libraries[i]) # calculate and show free space in each library
        print(i, ":", round(free / pow(1024, 3), 2), "GB free")

    print("\n\nGames:")
    for game in [acf for acf in acf_files if acf.lib in libraries_to_check]: # print appid, name, library, and size of each game
        print(game.get("appid"), game.get("name"), "on", game.lib, game.get_size(), "GB")


def move(params=None):
    if not params or len(params) != 2:
        # if 2 params aren't supplied ask for the game ID and destination
        params = [input("Enter Game ID / Name: "), input("Enter Destination Library: ")] 
    game_id = params[0]
    source = [game for game in acf_files if game.get("appid") == game_id or game.get("name") == game_id] # get matching games

    if source and len(source) == 1:
        source = source[0]
    elif source:
        print("Game is ambiguous.")
    else:
        print("Game not found.")
        return
    
    # if game and destination are valid move the game
    dest = params[1].lower()
    if dest in libraries:
        print("Moving Game...")
        source.move(dest)
        print("Done.")
    else:
        print("Library not found.")
        return


def delete(params=None):
    if not params:
        params = [input("Enter Game ID / Name: ")]
    game_id = params[0]

    source = [game for game in acf_files if game.get("appid") == game_id or game.get("name") == game_id] # get matching games
    if source and len(source) == 1:
        source = source[0]
    else: 
        print("Game is invalid or ambiguous")
        return
    
    # if game is valid then delete acf and directory
    print("Deleting...")
    remove(source.get_acf())
    shutil.rmtree(source.get_path())
    print("Done.")


def optimise(params=None):
    if not params:
        params = [input("Source Library: "), input("Destination Library: ")]
    source = params[0].lower()
    dest = params[1].lower()

    _, _, free = shutil.disk_usage(libraries[dest])
    free_gb = round(free / pow(1024, 3), 2)
    free_gb -= reserve

    # get games and sizes in source library and sort by reverse size
    games = [(acf, acf.get_size()) for acf in acf_files if acf.lib == source]
    games = sorted(games, key=lambda x: x[1], reverse=True)

    # move games until the reserve space is met in the destination library
    for acf, size in games:
        if size <= free_gb:
            if dest in libraries:
                print("Moving", acf.get("name"), "...")
                free_gb -= size
                acf.move(dest)
    print("Finished")


def list_compat(params=None):
    if params is None:
        pass
    for directory in compat:
        compat_dirs = [x for x in listdir(compat[directory])]
        print(compat_dirs)


optimise_command = Command("optimise", "o", "Move games to fill a specific drive", optimise)
compat_command = Command("compat", "c", "List compat data directories", list_compat)
delete_command = Command("delete", "d", "Delete a game", delete)
move_command = Command("move", "m", "Move a game", move)
list_command = Command("list", "l", "List games on all libraries", list_games)
commands: {Command} = {help_command, list_command, move_command, delete_command, optimise_command, compat_command}

# list all commands
def list_help(params=None):
    if params is None:
        pass
    print("Steam Storage:")
    for command in commands:
        print("\t-" + command.short, "--" + command.long, command.description)


help_command.fun = list_help

args: [str] = argv[1:]

# if no command then print help
if len(args) == 0:
    args = ["-h"]

cmd = args[0]
functions = [x.fun for x in commands if re.search("(-"+x.short+"|--"+x.long+")", cmd)]

# run command or print help
if not functions:
    print("Command", cmd, "not found.")
    functions = [list_help]
if len(functions) > 1:
    print(cmd, "is ambiguous")
    functions = [list_help]
functions[0](args[1:])
