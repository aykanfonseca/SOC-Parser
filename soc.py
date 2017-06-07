'''Python program to scrape UC San Diego's Schedule of Classes.'''

'''Created by Aykan Fonseca.'''

"""TODO UPDATES"""
# 1. Dictionaries as they are around 25% faster.
#       a. Retool get_data to make use of dictionaries to offer faster insert / lookup.
#       b. Retool parsing algorithms (parse_list & parse_list_sections) to split into corresponding portions.
# 2. Parse data on schedule of class web page - no need for SUBJECTS_URL.
#       a. Implement new way to find data.

# Builtins.
import itertools
import re
import sys
import time

# Pip install packages.
from bs4 import BeautifulSoup
from cachecontrol import CacheControl
from firebase import firebase
import requests

print(sys.version)

"""Some brief information. This program is comptabile with python 2.6+ & 3.0+.
   You must have all of the required packages installed as listed under 'pip
   installed packages'. This program also has diagnostic & timing output."""

"""Additionally, there are two cases where the program can exit prematurely.
   Both make use of sys.exit. The first is if we are missing a case in parsing
   the section information. The second is if the hashing algorithm which
   generates a unique key for each class encounters a collision (i.e:
   duplicate keys). Both of these are required to prevent corruption of db
   data."""

# Global Variables.
number_pages = 0
s = requests.Session()
times = []
times2 = []

# Starts the timer.
start = time.time()

# Create a timestamp for the start of scrape in year-month-day-hour-minute.
stamp = int(time.strftime("%Y%m%d%H%M"))

# Current year and next year but only the last two digits.
YEAR = int(time.strftime("%Y"))
currAndNextYear = (repr(YEAR % 100), repr(YEAR + 1 % 100))

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
    'schEndAmPm': '0'
}


def get_quarters(url, current=None):
    '''Gets all the quarters listed in drop down menu.'''

    quarters = s.get(url, stream=True)
    q_soup = BeautifulSoup(quarters.content, 'lxml').findAll('option')

    # Gets the rest of the quarters for the year.
    quarters = {}
    for option in q_soup:
        # Value will take the form 'FA16' or 'SP15' for example.
        value = option['value']
        if value[2:] in currAndNextYear:
            # Current quarter by optional parameter. Otherwise, always append.
            if current:
                return value

            quarters.append(value)

    return quarters


def get_subjects():
    '''Gets all the subjects listed in select menu.'''

    # Makes the post request for the Subject Codes.
    subject_post = requests.post(SUBJECTS_URL)
    soup = BeautifulSoup(subject_post.content, 'lxml').findAll('td')

    # Gets all the subject codes for post request.
    subjects = dict()

    # Doesn't matter if i.text is unicode. Still works fine.
    subjects['selectedSubjects'] = [i.text for i in soup if len(i.text) <= 4]

    return subjects


def update_term():
    '''Updates post request using current quarter by calling get_quarter.'''

    quarter = get_quarters(SOC_URL, current='yes')
    # term = {'selectedTerm': quarter}
    term = {'selectedTerm': "SA17"}
    # term = {'selectedTerm': "SP17"}
    # term = {'selectedTerm': "WI17"}
    POST_DATA.update(term)
    return quarter


def update_subjects():
    '''Updates the post request and subjects selected by parsing URL2.'''

    POST_DATA.update(get_subjects())
    # POST_DATA.update({'selectedSubjects': 'CSE'})
    # POST_DATA.update({'selectedSubjects' : 'BENG'})


def update_post():
    '''Calls updateSubjects & update_term to add to post data.'''

    update_subjects()
    return update_term()


def get_data(url, page):
    '''Parses the data of one page.'''

    pstart = time.time()

    # Occasionally, the first call will fail.
    try:
        post = s.get(url, stream=True)
    except requests.exceptions.HTTPError:
        post = s.get(url, stream=True)

    # Parse the response into HTML and look only for tr tags.
    tr_elements = BeautifulSoup(post.content, 'lxml').findAll('tr')

    # This will contain all the classes for a single page.
    page_list = []

    pstart2 = time.time()

    # Used to switch departments.
    for item in tr_elements:
        try:
            parsed_text = str(" ".join(item.text.split()).encode('utf_8'))
        except UnicodeEncodeError:
            pass
            # return sys.exit()

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
            page_list.append(str(current_dept + " " + add))

        # Exam Information, Section information, and Email.
        else:
            # Check if there is an item class.
            try:
                item_class = str(item['class'][0])

                if item_class == 'nonenrtxt':
                    if ('FI' or 'MI') in parsed_text:
                        page_list.append(str(parsed_text))

                elif item_class == 'sectxt':
                    if 'Cancelled' not in parsed_text:
                        # Check if there is an email.
                        try:
                            email = str(item.find('a')['href'])[7:]
                        except TypeError:
                            email = 'No Email'

                        page_list.append(str('....' + parsed_text))
                        page_list.append(str(email))

            except KeyError:
                pass

    pend = time.time()
    print ("Completed Page {} of {}".format(page, number_pages))
    times2.append(pend - pstart2)
    times.append(pstart2 - pstart)
    return page_list


def parse_list_sections(section, tracker, item):
    '''Parses the section information for parse_list.'''

    number_regex = re.compile(r'\d+')
    days_regex = re.compile(r'[A-Z][^A-Z]*')

    num_loc = number_regex.search(item).start()
    to_parse = item.split(' ')

    # ID.
    if num_loc == 4:
        section.append(item[4:10].strip())
        to_parse = to_parse[1:]
    else:
        section.append('Blank')
        to_parse[0] = to_parse[0][4:]

    # Meeting type and Section.
    section.extend(to_parse[0:2])

    # Readjust the list.
    to_parse = to_parse[2:]

    # Days: so MWF would have separate entries, M, W, F. Max = 5.
    if to_parse[0] != 'TBA':
        temp = days_regex.findall(to_parse[0])
        # Day 1, Day 2, Day 3, Day 4, and Day 5.
        if len(temp) == 5:
            section.extend(temp)
        if len(temp) == 4:
            section.extend(temp)
            section.append('Blank')
        if len(temp) == 3:
            section.extend(temp)
            section.extend(('Blank', 'Blank'))
        if len(temp) == 2:
            section.extend(temp)
            section.extend(('Blank', 'Blank', 'Blank'))
        if len(temp) == 1:
            section.extend((temp[0], 'Blank', 'Blank', 'Blank', 'Blank'))
        to_parse = to_parse[1:]
    else:
        section.extend(('Blank', 'Blank', 'Blank', 'Blank', 'Blank'))

    # The times.
    if to_parse[0] != 'TBA':
        section.extend(to_parse[0].partition('-')[::2])
        to_parse = to_parse[1:]
    else:
        section.extend(('Blank', 'Blank'))

    # Adjust list because time was given, but not building or room.
    if (len(to_parse) > 1) and (to_parse[0] == to_parse[1] == 'TBA'):
        to_parse = to_parse[1:]

    # The Building.
    if to_parse[0] != 'TBA':
        section.append(to_parse[0])
        to_parse = to_parse[1:]
    else:
        section.append('Blank')

    # The Room.
    if to_parse[0] != 'TBA':
        section.append(to_parse[0])
    else:
        section.append('Blank')

    # Readjust the list.
    to_parse = ' '.join(to_parse[1:])

    # Find position of first number in string.
    try:
        num_loc = number_regex.search(to_parse).start()
    except AttributeError:
        num_loc = 0

    # Handles Teacher, Seats Taken, and Seats Offered.
    if 'FULL' in to_parse:
        temp = to_parse.find('FULL')

        if temp == 0:
            section.extend(('Blank', 'Blank', 'Blank'))
        else:
            if 'Staff' in to_parse:
                section.extend(('Staff', 'Blank', 'Blank'))
            else:
                name = to_parse[:temp - 1].partition(',')

                # First name & last name.
                section.extend((name[0], name[2][1:].split(' ')[0]))

                # Middle name.
                try:
                    section.append(name[2][1:].split(' ')[1])
                except IndexError:
                    section.append('Blank')

        # Adjust String.
        to_parse = to_parse[temp:]

        # Amount of seats taken (WAITLIST Full).
        tracker[stamp] = int(to_parse[to_parse.find('(')+1:to_parse.find(')')])

        # Seats Taken.
        section.append(to_parse[:(to_parse.find(')')+1)])

        # Seats Available.
        section.append(to_parse[(to_parse.find(')')+2):])

    elif 'Unlim' in to_parse:
        if 'Staff ' in to_parse:
            # First, Last, middle names & Seat Information.
            section.extend(('Staff', 'Blank', 'Blank', 'Unlim', 'Unlim'))

            tracker[stamp] = -1
        else:
            name = to_parse[:to_parse.find('Unlim')-1].partition(',')

            # First name & last name.
            section.extend((name[0], name[2].strip().split(' ')[0]))

            # Middle name.
            try:
                section.append(name[2].strip().split(' ')[1])
            except IndexError:
                section.append('Blank')

            # -1 indicates unlimited seats.
            tracker[stamp] = -1

            # Seat information.
            section.extend(('Unlim', 'Unlim'))

    # Name and seat information.
    elif num_loc != 0:
        name = to_parse[:num_loc].strip().partition(',')

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

        temp = to_parse[num_loc:].strip().split(' ')

        # Amount of seats taken (has seats left over.).
        tracker[stamp] = int(temp[0])

        section.extend((temp[0], temp[1]))

    # Just staff and no seat information.
    elif to_parse.strip() == 'Staff':
        section.extend(('Staff', 'Blank', 'Blank', 'Blank', 'Blank'))

    # Name and no seat information.
    elif num_loc == 0 and ',' in to_parse:
        name = to_parse.strip().partition(',')

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

    # No name but seat info - think discussion sections without teacher name.
    elif num_loc == 0 and to_parse:
        try:
            section.extend(('Blank', 'Blank', 'Blank'))
            temp = to_parse.split(' ')

            tracker[stamp] = int(temp[0])

            section.append(int(temp[0]))
            section.append(int(temp[1]))

        except IndexError:
            print("ERROR")
            sys.exit()

    # No name and no seat information
    else:
        section.extend(('Blank', 'Blank', 'Blank', 'Blank', 'Blank'))
        # TODO: Add tracker information.


def check_collision_key(ls):
    '''Compares all keys and makes sure they are unique.'''

    seen = set()
    differences = []

    for item in ls:
        for i in item:
            if isinstance(i, int):
                if i not in seen:
                    seen.add(i)
                else:
                    differences.append(i)

    # This will print the sizes. If collision, they will be different.
    print("---Diagonistic Information---")
    print("  - # of keys: " + str(len(seen) + len(differences)))
    print("  - # of unique keys: " + str(len(seen)))
    print("  - Note: We want them to be the same.")
    print("")

    # This code will print the keys that collided in a list.
    if differences:
        print(differences)
        return False

    return True


def generate_key(header, section, final):
    '''Gives a unique ID to use. If a disc. id, use it, else use lecture id.'''

    # TODO: Update Hash key generation.
    tempKey = ''.join(header[:2]) + ''.join(section[2:5]) + section[9]
    tempKey += ''.join(section[12:15])

    try:
        return hash(tempKey + section[17])
    except IndexError:
        return hash(tempKey + section[0])


def parse_list(ls):
    '''Parses the list elements into their readable values to store.'''

    # Components of a class.
    header = []
    email = []
    final = []
    midterm = []
    section = []
    tracker = {}

    number_regex = re.compile(r'\d+')

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

        # What happens with two emails? Need to modify getData as well.

        # Find Email Info.
        if (('No Email' in item) or ('.edu' in item)) and (item.strip() not in email):
            if (not email) or ('No Email' not in item):
                email.append(item.strip())

        # Finds Section Info.
        if '....' in item:
            parse_list_sections(section, tracker, item)

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

    # FIXME: How to reduce function call to generate_key?
    key = generate_key(header, section, final)

    key_tracker = dict()
    key_tracker = {key: [tracker]}

    """Important: If you have a list of collision keys,
       put one in here to determine the problematic classes."""
    # if (key == -5895194357248003337):
    #     print(header, section, tracker)

    return [header, section, email, midterm, final, key_tracker, key]


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

    with open("tracking.txt", "w") as open_file2:
        with open("dataset2.txt", "w") as open_file:
            for item in ls:
                for i in item:
                    if isinstance(i, dict):
                        open_file2.write(str(i))
                        open_file2.write("\n")
                        open_file2.write("\n")
                    elif isinstance(i, int):
                        pass
                    else:
                        open_file.write(str(i))

                open_file.write("\n")
                open_file.write("\n")


def write_to_db(ls):
    # TODO: Add entry script.

    db = firebase.FirebaseApplication("https://schedule-of-classes.firebaseio.com")

    path = "/Classes/quarter/SUMMER 2017/"

    for i in ls:
        key = i[-1]
        result = db.post(path + str(key), i[:-2])


def main():
    '''The main function.'''

    # TODO: Condense Main function to minimal amount of "setup" code

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

    # FIXME: BOTTLE NECK
    post = s.post(SOC_URL, data=POST_DATA, stream=True)

    # B
    check2 = time.time()

    # Define rough boundaries where the page number should be.
    begin = int(re.search(r"Page", str(post.content)).start()) + 22

    # The total number of pages to parse and the current page starting at 1.
    number_pages = int(str(post.content)[begin:begin + 6].partition(')')[0])

    # Prints which quarter we are fetching data from and how many pages.
    print("Fetching data for {} from {} pages\n".format(quarter, number_pages))

    # C
    check3 = time.time()

    pages = list(range(1, number_pages + 1))
    urls = (SOC_URL + str(x) for x in pages)

    # Groups a url with its page number.
    tied = zip(urls, pages)

    # Gets the data using urls.
    # FIXME: Retool get_data to accept a tuple object and return a list so we avoid function calls.
    # FIXME 2: Also retool get_data along with other methods to work with dictionaries which offer faster lookup & insert.
    results = [get_data(x, y) for (x, y) in tied]

    # Explicitly close connection.
    r = requests.post(url=SOC_URL, headers={'Connection':'close'})

    # D
    check4 = time.time()

    # Format list into proper format
    results = format_list(results)

    # E
    check5 = time.time()

    # Parses items in list into usable portions.
    # FIXME: Remove function call - as they are expensive - and put for loop in parse_list.
    final = [parse_list(item) for item in results]

    # F
    check6 = time.time()

    # Does the printing of the timing statements.
    print("\n")
    print('---This is the break down of code timing:---')
    print('\t' + '0 --  ' + str(check0 - start))
    print('\t' + 'A --  ' + str(check1 - start))
    print('\t' + 'B --  ' + str(check2 - start))
    print('\t' + 'C --  ' + str(check3 - start))
    print('\t' + 'D --  ' + str(check4 - start))
    print('\t' + 'E --  ' + str(check5 - start))
    print('\t' + 'F --  ' + str(check6 - start) + '\n')

    print("---Meta Timing Information---")
    print("  - This is how long the requests take: " + str(sum(times)))
    print("\tAverage: " + str(float(sum(times)) / max(len(times), 1)))
    print("  - This is how long the parsing take: " + str(sum(times2)))
    print("\tAverage: " + str(float(sum(times2)) / max(len(times2), 1)) + "\n")

    return final


if __name__ == '__main__':
    DONE = main()

    # If our unique ID keys aren't for some reason unique, we want to stop.
    if check_collision_key(DONE) is False:
        print("ERROR: Hashing algorithm encountered a collision!")
        sys.exit()

    # Ends the timer.
    END = time.time()

    # Writes the data to a file.
    write_data(DONE)

    # Prints how long it took for program to run with checkpoints.
    print('\n' + str(END - start))
