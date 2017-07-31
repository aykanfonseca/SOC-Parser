# SOC Parser
Parses the schedule of classes. The program is extensible and has few functions. It can scrape data from any quarter specified and all or specific subjects. Also recently implemented is tracking on a per-class level. This program was built using Python and is compatible with Python 2.6+ and Python 3.0+ :snake:. It also is _mostly_ PEP8 compliant and has generous notes on functionality. Data is uploaded to firebase but can be swapped for another one.

## How to use (Mac) :computer:
There are a couple of python modules you must install first to run this program.

**NOTE**: If pip is already installed, proceed to step 3. 

1. Install [homebrew](https://brew.sh). This is a useful general package manager for macOS. 
2. Install Python via homebrew - `brew install python`. 
3. Install lxml - `pip install lxml`.
4. Install requests - `pip install requests`.
5. Install bs4 - `pip install bs4`.
6. Install cachecontrol - `pip install cachecontrol`.
7. Install firebase - `pip install python-firebase`.
8. (OPTIONAL) Python 3 setup: Install Python 3 via homebrew - `brew install python3`. Then, repeat steps 3-7 with `pip3` instead of `pip`.

## Coding Rules :straight_ruler:
1. Flexible and extensible. This means don't hard code values "FA16", "CSE", etc.. It also means we have a separation of concerns when it makes sense to do so. For example, we have separation of concerns for get_quarters and get_subjects to provide fine-tool optimizations when appropriate for either but also for specific scrapes (a future feature).
2. Readable and easy to understand. This means writing excellent comments, debug tools, and making lines shorter and simpler. This is a bit difficult, especially with the parse_list method which appears fairly archaic and magical unless we see visibly how the data is structured.

## Improvements to do :wrench:
* Account for multiple teachers, sections, emails, and more.
* Fix db schema to be more flat for efficient querying. Put everything in the header on the first level. 

#### TIPS :bulb:
* You can delete an entire firebase project and start from scratch.
* You can edit the files in Atom / Sublime Text 3 and open the directory containing the files in the terminal window using a keyboard shortcut (needs a package for both).
* Lint Python files using Pylint.

## Brief Explanations
* **`get_quarters`**: Retrieves all the quarters from the drop-down menu shown [here](https://act.ucsd.edu/scheduleOfClasses/scheduleOfClassesStudent.htm). For now, this function only retrieves quarters from the current and following year. This can be changed by altering `VALID_YEARS`.
* **`get_subjects`**: Retrieves all the subjects from the multi-select menu shown [here](https://act.ucsd.edu/scheduleOfClasses/scheduleOfClassesStudent.htm). It does this by parsing this [page](http://blink.ucsd.edu/instructors/courses/schedule-of-classes/subject-codes.html) which includes all the subjects shown in the multi-select menu. 
* **`setup`**: This function does three things. First, it updates the post request with data gathered from `get_quarters`. Second, it updates the post request with data gathered from `get_subjects`. Finally, we submit the post request and find out the number of pages to parse. This number is then stored in `NUMBER_PAGES`. After this function is finished executing, we return the quarter we are parsing so we can print it out later.
