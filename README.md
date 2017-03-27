# SOC Parser
Parses the schedule of classes.

# How to use (Mac)
There are a couple of python modules you must install first to run this program.

If you already have pip installed, you can proceed to step 3.

1. Install homebrew. This is a useful general package manager for macOS.
2. Install python via homebrew. Doing so will get us pip. 
3. Install lxml via pip
4. Install requests via pip
5. Install bs4 via pip

# Improvements to do
1. Parallelize code via map and grequests.
2. Eliminate timing code.
3. Eliminate partitioning code and insert page number directly into the function.
4. Load data into database for retreival.
5. Account for multiple teachers, sections, emails, and more.
6. Fine-tune data to create a class object with metrics for a particular class.
  a. How many discussions are avaiable.

