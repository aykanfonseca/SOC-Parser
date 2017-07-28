# SOC Parser
Parses the schedule of classes. The program is extensible and has few functions. It can scrape data from any quarter specified and all or specific subjects. Also recently implemented is tracking on a per-class level.

## How to use (Mac)
There are a couple of python modules you must install first to run this program.

**NOTE: Repeat steps 3-6 with pip3 for python3 setup.**

If you already have pip installed, you can proceed to step 3.

1. Install [homebrew](https://brew.sh). This is a useful general package manager for macOS. 
2. Install Python via homebrew to get Python's package mananger pip. This can be done by typing into a terminal, `pip install python`. The following steps will also use pip for a Python 2 setup. Type the commands into a terminal window. 
3. Install lxml - `pip install lxml`.
4. Install requests - `pip install requests`.
5. Install bs4 - `pip install bs4`.
6. Install cachecontrol - `pip install cachecontrol`.

## Improvements to do
1. Account for multiple teachers, sections, emails, and more.

### TIPS
1. You can delete an entire firebase project and start from scratch.
