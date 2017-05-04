'''Python program to scrape UC San Diego's Schedule of Classes.'''

# Builtins. Note: from__future__ is required to be first.
from __future__ import print_function
import re
import itertools
import time
from datetime import datetime

# Pip install packages.
import requests
from bs4 import BeautifulSoup
from cachecontrol import CacheControl

# Global Variables.
s = requests.Session()
number_pages = 0
times = []
times2 = []

# Starts the timer.
start = time.time()

# Current year (CY) and next year (NY) but only the last two digits.
YEAR = datetime.now().year
CY = repr(YEAR % 100)
NY = repr(YEAR + 1 % 100)

# URL to the entire list of classes.
SOC_URL = 'https://act.ucsd.edu/scheduleOfClasses/scheduleOfClassesStudentResult.htm?page='

# URL to get the 3 - 4 letter department codes.
SUBJECTS_URL = 'http://blink.ucsd.edu/instructors/courses/schedule-of-classes/subject-codes.html'

# Input data besides classes.
POST_DATA = {
    'loggedIn': 'false',
    'instructorType': 'begin',
    'titleType': 'contain',
    'schDay': ['M', 'T', 'W', 'R', 'F', 'S'],
    'schedOption1': 'true',
    'schedOption2': 'true',
    'schStartTime': '12:00',
    'schStartAmPm': '0',
    'schEndTime': '12:00',
    'schEndAmPm': '0',
    'tabNum': 'tabs-sub',
    'schedOption1Dept': 'true',
    'schedOption2Dept': 'true',
    'schDayDept': ['M', 'T', 'W', 'R', 'F', 'S'],
    'schStartTimeDept': '12:00',
    'schStartAmPmDept': '0',
    'schEndTimeDept': '12:00',
    'schEndAmPmDept': '0'
}


def get_quarters(url, current=None):
    '''Gets all the quarters listed in drop down menu.'''

    quarters = requests.get(url)
    q_soup = BeautifulSoup(quarters.content, 'lxml')

    # Gets the rest of the quarters for the year.
    quarters = []
    for option in q_soup.findAll('option'):
        # Value will take the form 'FA16' or 'SP15' for example.
        value = option['value']
        if value[2:] in (CY, NY):
            # Current quarter by optional parameter.
            if current:
                return value
            else:
                quarters.append(value)

    return quarters


def get_subjects():
    '''Gets all the subjects listed in select menu.'''

    # Makes the post request for the Subject Codes.
    subject_post = requests.post(SUBJECTS_URL, stream=True)
    subject_soup = BeautifulSoup(subject_post.content, 'lxml')

    # Gets all the subject Codes for post request.
    subjects = {}
    for i in subject_soup.findAll('td'):
        if len(i.text) <= 4:
            if str(i.text).isupper():
                subjects.setdefault('selectedSubjects', []).append(str(i.text))

    return subjects


def update_term():
    '''Updates post request using current quarter by calling get_quarter.'''

    quarter = get_quarters(SOC_URL, current='yes')
    term = {'selectedTerm': quarter}
    # term = {'selectedTerm': "SP17"}
    # term = {'selectedTerm': "WI17"}
    POST_DATA.update(term)
    return quarter


def update_subjects():
    '''Updates the post request and subjects selected by parsing URL2.'''

    POST_DATA.update(get_subjects())
    # POST_DATA.update({'selectedSubjects' : 'CSE'})
    # POST_DATA.update({'selectedSubjects' : 'BENG'})


def update_post():
    '''Calls updateSubjects & update_term to add to post data.'''

    update_subjects()
    quarter = update_term()
    return quarter


def get_data(url, page):
    '''Parses the data of one page.'''

    pstart = time.time()

    # Occasionally, the first call will fail.
    try:
        post = s.get(url, stream=True)
    except requests.exceptions.HTTPError:
        post = s.get(url, stream=True)

    pstart2 = time.time()

    # Parse the response into HTML and look only for tr tags.
    tr_elements = BeautifulSoup(post.content, 'lxml').findAll('tr')

    # This will contain all the classes for a single page.
    page_list = []

    # Used to switch departments.
    for item in tr_elements:
        try:
            parsed_text = str(" ".join(item.text.split()).encode('utf-8'))
        except UnicodeEncodeError:
            return "error"

        # Changes department if tr_element looks like a department header.
        try:
            check = item.td.h2.text

            # We have a 3-4 department code in our tag.
            if " )" in check:
                current_dept = str(check.partition("(")[2].partition(" ")[0])

        # Not on a department, so skip it, and use previous current_dept.
        except AttributeError:
            pass

        # The header of each class: units, department, course number, etc..
        if 'Units' in parsed_text:
            page_list.append((' NXC'))
            add = parsed_text.partition(' Prereq')[0]
            page_list.append((current_dept + " " + add))

        # Exam Information, Section information, and Email.
        else:
            # Check if there is an item class.
            try:
                item_class = str(item['class'][0])

                if item_class == 'nonenrtxt':
                    if ('FI' or 'MI') in parsed_text:
                        page_list.append((parsed_text))

                elif item_class == 'sectxt':
                    if 'Cancelled' not in parsed_text:
                        # Check if there is an email.
                        try:
                            email = str(item.find('a')['href'])[7:]
                        except TypeError:
                            email = 'No Email'

                        page_list.append(('....' + parsed_text))
                        page_list.append((email))

            except KeyError:
                pass

    pend = time.time()
    print ("Completed Page {} of {}".format(page, number_pages))
    times.append(pend - pstart2)
    times2.append(pstart2 - pstart)
    return page_list


def parse_list_sections(section, item):
    '''Parses the section information for parse_list.'''

    number_regex = re.compile(r'\d+')
    days_regex = re.compile(r'[A-Z][^A-Z]*')

    num_loc = number_regex.search(item).start()
    S = item.split(' ')

    # ID.
    if num_loc == 4:
        section.append(item[4:10].strip())
        S = S[1:]
    else:
        section.append('Blank')
        S[0] = S[0][4:]

    # Meeting type and Section.
    section.extend(S[0:2])

    # Readjust the list.
    S = S[2:]

    # Days: so MWF would have separate entries, M, W, F.
    if S[0] != 'TBA':
        temp = days_regex.findall(S[0])
        # Day 1, Day 2, and Day 3.
        if len(temp) == 3:
            section.extend(temp)
        if len(temp) == 2:
            section.extend((temp, 'Blank'))
        if len(temp) == 1:
            section.extend((temp[0], 'Blank', 'Blank'))
        S = S[1:]
    else:
        section.extend(('Blank', 'Blank', 'Blank'))

    # The times.
    if S[0] != 'TBA':
        section.extend(S[0].partition('-')[::2])
        S = S[1:]
    else:
        section.extend(('Blank', 'Blank'))

    # Adjust list because time was given, but not building or room.
    if (len(S) > 1) and (S[0] == S[1] == 'TBA'):
        S = S[1:]

    # The Building.
    if S[0] != 'TBA':
        section.append(S[0])
        S = S[1:]
    else:
        section.append('Blank')

    # The Room.
    if S[0] != 'TBA':
        section.append(S[0])
    else:
        section.append('Blank')

    # Readjust the list.
    S = ' '.join(S[1:])

    # Find position of first number in string.
    try:
        num_loc = number_regex.search(S).start()
    except AttributeError:
        num_loc = 0

    # Handles Teacher, Seats Taken, and Seats Offered.
    if 'FULL' in S:
        temp = S.find('FULL')

        if temp == 0:
            section.extend(('Blank', 'Blank', 'Blank'))
        else:
            if 'Staff' in S:
                section.extend(('Staff', 'Blank', 'Blank'))
            else:
                name = S[:temp - 1].partition(',')

                # First name & last name.
                section.extend((name[0], name[2][1:].split(' ')[0]))

                # Middle name.
                try:
                    section.append(name[2][1:].split(' ')[1])
                except IndexError:
                    section.append('Blank')

        # Adjust String.
        S = S[temp:]

        # Seats Taken.
        section.append(S[:(S.find(')')+1)])

        # Seats Available.
        section.append(S[(S.find(')')+2):])

    elif 'Unlim' in S:
        if 'Staff ' in S:
            # First, Last, middle names & Seat Information.
            section.extend(('Staff', 'Blank', 'Blank', 'Unlim', 'Unlim'))
        else:
            name = S[:S.find('Unlim')-1].partition(',')

            # First name & last name.
            section.extend((name[0], name[2].strip().split(' ')[0]))

            # Middle name.
            try:
                section.append(name[2].strip().split(' ')[1])
            except IndexError:
                section.append('Blank')

            # Seat information.
            section.extend(('Unlim', 'Unlim'))

    # Name and seat information.
    elif num_loc != 0:
        name = S[:num_loc].strip().partition(',')

        # First name.
        if name[0] != '':
            section.append(name[0])
        else:
            section.append('Blank')

        # Last name.
        if name[2].strip().split(' ')[0] != '':
            section.append(name[2].strip().split(' ')[0])
        else:
            section.append('Blank')

        # Middle name.
        try:
            section.append(name[2].strip().split(' ')[1])
        except IndexError:
            section.append('Blank')

        temp = S[num_loc:].strip().split(' ')
        section.extend((temp[0], temp[1]))

    # Just staff and no seat information.
    elif S.strip() == 'Staff':
        section.extend(('Staff', 'Blank', 'Blank', 'Blank', 'Blank'))

    # Name and no seat information.
    elif num_loc == 0:
        name = S.strip().partition(',')

        # First name.
        if name[0] != '':
            section.append(name[0])
        else:
            section.append('Blank')

        # Last name.
        if name[2].strip().split(' ')[0] != '':
            section.append(name[2].strip().split(' ')[0])
        else:
            section.append('Blank')

        # Middle name.
        try:
            section.append(name[2].strip().split(' ')[1])
        except IndexError:
            section.append('Blank')

        # Blanks for both the seat information.
        section.extend(('Blank', 'Blank'))

    # No name and no seat information
    else:
        section.extend(('Blank', 'Blank', 'Blank', 'Blank', 'Blank'))


def parse_list(ls):
    '''Parses the list elements into their readable values to store.'''

    # Components of a class.
    header = []
    email = []
    final = []
    midterm = []
    section = []

    number_regex = re.compile(r'\d+')
    # days_regex = re.compile(r'[A-Z][^A-Z]*')

    for item in ls:
        # Find class information.
        if 'Units' in item:
            # Department.
            c_department = item.partition(' ')[0]
            header.append(c_department)
            num_loc = number_regex.search(item).start()

            # Course Number.
            c_number = item[num_loc:].partition(' ')[0]

            header.append(c_number)

            # Temporary variable to make lines shorter and save time.
            temp = item.partition('( ')

            # Name.
            header.append(temp[0][len(c_number) + 1 + num_loc: -1])

            # Units.
            header.append(temp[2].partition(')')[0])

            # Restrictions.
            if num_loc != len(c_department) + 1:
                header.append(item[len(c_department) + 1: num_loc - 1])
            else:
                header.append('No Restrictions')

        # TODO: What happens with two emails? Need to modify getData as well.

        # Find Email Info.
        if (('No Email' in item) or ('.edu' in item)) and (item.strip() not in email):
            if (len(email) == 0) or ('No Email' not in item):
                email.append(item.strip())

        # Finds Section Info.
        if '....' in item:
            parse_list_sections(section, item)

        # Finds Final / Midterm Info.
        if ('FI' or 'MI') in item:
            exam = item.split(' ')

            temp = []

            temp.extend(exam[1:3])

            # The start and end times.
            if exam[3] != 'TBA':
                temp.extend(exam[3].partition('-')[::2])
            else:
                temp.extend(('TBA', 'TBA'))

            temp.extend(exam[4:])

            if 'FI' in item:
                final = temp
            else:
                midterm = temp

    return [header, section, email, midterm, final]


def format_list(ls):
    '''Formats the result list into the one we want.'''

    # Flattens list of lists into list.
    parsed = (item for sublist in ls for item in sublist)

    # Groups list into lists of lists based on a delimiter word.
    parsed = (list(y) for x, y in itertools.groupby(parsed, lambda z: z == ' NXC') if not x)

    # Sorts list based on sorting criteria.
    return (x for x in parsed if len(x) > 2 and 'Cancelled' not in x)


def write_data(ls):
    '''Writes the data to a file.'''

    with open("dataset3.txt", "w") as open_file:
        for item in ls:
            for i in item:
                open_file.write(str(i))

            open_file.write("\n")
            open_file.write("\n")


def main():
    '''The main function.'''

    # Global Variables.
    global s
    global number_pages
    global times
    global times2

    times = []
    times2 = []

    # 0
    check0 = time.time()

    # Update postData and request session for previously parsed classes.
    quarter = update_post()

    # A
    check1 = time.time()

    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0'
    s = CacheControl(s)

    # BOTTLE NECK
    post = s.post(SOC_URL, data=POST_DATA, stream=True)
    soup = BeautifulSoup(post.content, 'lxml')

    # B
    check2 = time.time()

    # Define rough boundaries where the page number should be.
    begin = int(re.search(r"Page", soup.text).start() + 12)
    finish = begin + 8

    # The total number of pages to parse and the current page starting at 1.
    number_pages = int(soup.text[begin:finish].partition(')')[0])

    # Prints which quarter we are fetching data from and how many pages.
    print("Fetching data for {} from {} pages\n".format(quarter, number_pages))

    # C
    check3 = time.time()

    pages = [x for x in xrange(1, number_pages + 1)]
    urls = (SOC_URL + str(x) for x in pages)

    # Gets the data using urls.
    results = (get_data(x, y) for (x, y) in itertools.izip(urls, pages))

    # D
    check4 = time.time()

    # Format list into proper format
    results = (format_list(results))

    # E
    check5 = time.time()

    # Parses items in list into usable portions.
    final = [parse_list(item) for item in results]

    # F
    check6 = time.time()

    # Does the printing of the timing statements.
    print('This is the break down of code timing:\n')
    print('\t' + '0 --  ' + str(check0 - start))
    print('\t' + 'A --  ' + str(check1 - start))
    print('\t' + 'B --  ' + str(check2 - start))
    print('\t' + 'C --  ' + str(check3 - start))
    print('\t' + 'D --  ' + str(check4 - start))
    print('\t' + 'E --  ' + str(check5 - start))
    print('\t' + 'F --  ' + str(check6 - start) + '\n')

    print("This is how long the requeests take: " + str(sum(times)))
    print("\tAverage: " + str(float(sum(times)) / max(len(times), 1)))
    print("This is how long the parsing take: " + str(sum(times2)))
    print("\tAverage: " + str(float(sum(times2)) / max(len(times2), 1)))

    return final


if __name__ == '__main__':
    done = main()

    # Ends the timer.
    end = time.time()

    # Writes the data to a file.
    write_data(done)

    # Prints how long it took for program to run with checkpoints.
    print('\n' + str(end - start))
