# Steam Achievement Tracker

A small desktop widget that sits on top of your other windows and shows you how close you are to unlocking Steam achievements, for any game in your library, while you play. You pick which achievements to keep an eye on and the widget checks your progress for you every so often.

This guide is written for people who have never used something like this before. You do not need to know how to write code to set it up.

## Table of contents

- [What you need before you start](#what-you-need-before-you-start)
- [Setting up](#setting-up)
  - [Step 1: Install Python](#step-1-install-python)
  - [Step 2: Get a Steam Web API key](#step-2-get-a-steam-web-api-key)
  - [Step 3: Find your SteamID64](#step-3-find-your-steamid64)
  - [Step 4: Make your Steam profile public](#step-4-make-your-steam-profile-public)
- [Starting the program](#starting-the-program)
- [How to use it](#how-to-use-it)
  - [The floating window](#the-floating-window)
  - [Adding a game](#adding-a-game)
  - [Pinning an achievement](#pinning-an-achievement)
  - [Pinning a stat as a goal](#pinning-a-stat-as-a-goal)
  - [Removing a pinned item](#removing-a-pinned-item)
  - [Moving the window](#moving-the-window)
  - [Changing the colors and transparency](#changing-the-colors-and-transparency)
  - [The right-click menu](#the-right-click-menu)
- [Why some games do not show any stats](#why-some-games-do-not-show-any-stats)
- [Troubleshooting](#troubleshooting)
- [Your data stays on your computer](#your-data-stays-on-your-computer)

## What you need before you start

- A Windows computer.
- A Steam account with some games on it.
- Your Steam profile and game details set to public. This is explained below.
- About ten minutes for the one-time setup.

## Setting up

You only need to do this once. After that, starting the program takes one click.

### Step 1: Install Python

This program is written in a language called Python. Your computer needs Python installed to run it, the same way it needs a web browser installed to open a webpage.

1. Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest version for Windows.
2. Run the installer. On the very first screen, tick the box that says "Add python.exe to PATH" before clicking Install.
3. Finish the installation.

If Python is already installed on your computer, you can skip this step.

### Step 2: Get a Steam Web API key

The program needs a key from Steam to be allowed to read your achievement progress. This is free and only takes a minute.

1. Go to [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey) and log in with your Steam account.
2. For "Domain Name" you can type anything, for example `localhost`.
3. Click Register. You will be given a key made of letters and numbers.
4. Keep this page open, or copy the key somewhere safe. You will need to paste it into the program in a moment.

Treat this key like a password. Do not share it with anyone or post it publicly.

### Step 3: Find your SteamID64

This is a long number that identifies your Steam account.

1. Go to [steamid.io](https://steamid.io/).
2. Paste in the link to your Steam profile page (you can find this by opening your profile in a browser and copying the address bar).
3. The site will show you several ID formats. Copy the one labeled `steamID64`. It is a long number, for example `76561198012345678`.

### Step 4: Make your Steam profile public

The program reads your achievement and stat data through Steam, and Steam only allows this if your profile is set to public.

1. Open Steam and go to your own profile.
2. Click Edit Profile, then Privacy Settings.
3. Set "My profile" to Public.
4. Set "Game details" to Public.
5. Save the changes.

You can change this back to private again later if you want, but the program will not be able to read your progress while it is private.

## Starting the program

Double-click the file named `start_achievement_tracker.bat` in this folder.

The first time you start it, a small setup window will appear asking for your Steam Web API key and your SteamID64. Paste in the values from the steps above and click "Save & Continue". The program checks that they work before continuing, so if you typed something wrong it will tell you.

If double-clicking the file does not do anything, it usually means Python was not added to PATH during installation. Reinstall Python and make sure to tick that box, or open a Command Prompt in this folder and type:

`python achievement_tracker.py`

## How to use it

### The floating window

Once set up, a small dark window appears in the corner of your screen. This is the tracker. It stays on top of other windows so you can glance at it while playing. At first it will say that nothing is pinned yet, because you have not chosen anything to track.

### Adding a game

Right-click anywhere on the floating window and choose "Manage achievements...". A larger window opens with a list of your games on the left.

Click "Add from library...". This opens a list of every game in your Steam library. You can type in the search box to find a game quickly. Select one or more games and click "Add selected".

### Pinning an achievement

In the Manage Achievements window, click a game in the list on the left. After a moment, its locked achievements appear in the list on the right, along with a bar showing how many achievements you have unlocked overall.

Double-click an achievement to pin it. It will now show up in the floating window. Where possible, the program automatically figures out which in-game statistic matches that achievement, so the floating window can show a live count such as "23 / 50" instead of just "locked". This does not always work, since not every achievement has a matching statistic, in which case it will simply show as locked or unlocked.

Double-click a pinned achievement again to unpin it.

### Pinning a stat as a goal

Below the achievements list is a list of the game's raw statistics, for example "Foundations built" or "Enemies killed". You can pin one of these directly as a personal goal, even if it is not tied to any achievement.

Double-click a stat, then type in the target number you are aiming for and a label to show on the tracker. It will then appear in the floating window with your current progress toward that number.

### Removing a pinned item

Right-click directly on a pinned item in the floating window. A menu appears with a "Remove" option at the top, specific to that item.

### Moving the window

Click and drag anywhere on the floating window, including its title bar or any of the pinned rows, and drop it wherever you like. Its position is remembered the next time you open the program.

### Changing the colors and transparency

Right-click the floating window and choose "Appearance...". A small window opens where you can click the color swatch to pick a new background color, and drag the slider to change how see-through the window is. Changes apply immediately.

### The right-click menu

Right-clicking the floating window (or a pinned item within it) gives you quick access to:

- Refresh now, to check your progress immediately instead of waiting.
- Manage achievements, to open the game and achievement picker.
- Appearance, to change colors and transparency.
- Edit Steam credentials, in case your API key changes or you want to switch accounts.
- Quit, to close the program.

## Why some games do not show any stats

Not every game on Steam reports detailed statistics to Steam, even if it has achievements. Games where progress is tracked by the game's own servers rather than by Steam, which is common for online multiplayer games, often will not have any statistics available at all. In that case the achievements list will still work, but the stats list underneath it will be empty, and pinned achievements for that game can only show as locked or unlocked rather than a live number. This is a limitation of what the game reports to Steam, not something the program can work around.

## Troubleshooting

**The setup window says it could not verify my key or ID.**
Double check that you copied the whole API key and the whole SteamID64 number without extra spaces. Also make sure your profile is set to public, as described in step 4 above.

**A game shows no achievements or an error when I click it.**
Make sure "Game details" is set to Public in your Steam privacy settings. Some games also simply have no achievements or stats configured by their developer.

**The floating window disappeared.**
It may have been dragged off the edge of the screen, or closed with the small X in its corner. Start the program again from `start_achievement_tracker.bat`, it will reopen wherever it last remembers being.

**I want to track a different Steam account.**
Right-click the floating window, choose "Edit Steam credentials...", and enter the new API key and SteamID64.

## Your data stays on your computer

Your API key, SteamID64, and the list of games and achievements you pin are saved in a file called `tracker_config.json` in this folder. Nothing is sent anywhere except to Steam's own servers, to read your public achievement and stat data. Nobody else can see this file unless they have access to your computer.
