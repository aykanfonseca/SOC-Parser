# SOC Parser
Parses the schedule of classes. The program is extensible and has few functions. It can scrape data from any quarter specified and all or specific subjects. Also recently implemented is tracking on a per-class level. This program was built using Python and is compatible with Python 2.6+ and Python 3.0+ :snake:. It also is _mostly_ PEP8 compliant and has generous notes on functionality. Data is uploaded to firebase but can be swapped for another one.

## How to use (Mac) :computer:
There are a couple of python modules you must install first to run this program.

**NOTE**: Repeat steps 3-6 with pip3 for python3 setup. If you already have pip installed, you can proceed to step 3.

1. Install [homebrew](https://brew.sh). This is a useful general package manager for macOS. 
2. Install Python via homebrew - `brew install python`. 
3. Install lxml - `pip install lxml`.
4. Install requests - `pip install requests`.
5. Install bs4 - `pip install bs4`.
6. Install cachecontrol - `pip install cachecontrol`.

## Improvements to do :wrench:
* Account for multiple teachers, sections, emails, and more.

#### TIPS :bulb:
* You can delete an entire firebase project and start from scratch.
