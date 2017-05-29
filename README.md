# SOC Parser
Parses the schedule of classes.

# How to use (Mac)
There are a couple of python modules you must install first to run this program.

___NOTE: Repeat steps 3-6 with pip3 for python3 setup.____

If you already have pip installed, you can proceed to step 3.

1. Install homebrew. This is a useful general package manager for macOS.
2. Install python via homebrew. Doing so will get us pip.
3. Install lxml via pip.
4. Install requests via pip.
5. Install bs4 via pip.
6. Install cachecontrol via pip.

# Improvements to do
1. Load data into database for retrieval.
2. Account for multiple teachers, sections, emails, and more.
3. Fine-tune data to create a class object with metrics for a particular class. I.e: How many discussions are available, enrollment figures, policies on waitlists, and more.
