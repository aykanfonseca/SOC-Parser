'''Python program to scrape UC San Diego's Schedule of Classes.'''

'''Created by Aykan Fonseca.'''

# TODO: Retool parsing algorithms to split into corresponding portions with Dictionaries.

# Builtins.
import collections
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

# Global Variables.
number_pages = 0
s = CacheControl(requests.Session())

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
    'schedOption2': 'true'
}


def get_quarters(url, current = None):
    '''Gets all the quarters listed in drop down menu.'''

    quarters = s.get(url, stream = True)
    q_soup = BeautifulSoup(quarters.content, 'lxml').findAll('option')

    # Gets the rest of the quarters for the year. For example, 'FA16' or 'SP15'.
    quarters = {}
    for option in q_soup:
        if option['value'][2:] in currAndNextYear:
            if current:
                return option['value']

            quarters.append(option['value'])

    return quarters


def get_subjects():
    '''Gets all the subjects listed in select menu.'''

    # Makes the post request for the Subject Codes.
    subject_post = requests.post(SUBJECTS_URL)
    soup = BeautifulSoup(subject_post.content, 'lxml').findAll('td')

    # Gets all the subject codes for post request.
    subjects = {}
    subjects['selectedSubjects'] = [i.text for i in soup if len(i.text) <= 4]

    return subjects


def update_data():
    '''Updates post request with quarter and subjects selected.'''

    quarter = get_quarters(SOC_URL, current='yes')
    # term = {'selectedTerm': quarter}
    term = {'selectedTerm': "SA17"}
    POST_DATA.update(term)

    # POST_DATA.update(get_subjects())
    POST_DATA.update({'selectedSubjects': 'CSE'})

    return quarter


def get_data(tied):
    '''Parses the data of one page.'''

    master = []

    for url, page in tied:
        # Occasionally, the first call will fail.
        try:
            post = s.get(url, stream=True)
        except requests.exceptions.HTTPError:
            post = s.get(url, stream=True)

        # Parse the response into HTML and look only for tr tags.
        tr_elements = BeautifulSoup(post.content, 'lxml').findAll('tr')

        # This will contain all the classes for a single page.
        page_list = []

        for item in tr_elements:
            parsed_text = str(" ".join(item.text.split()).encode('utf_8'))

            # Changes department if tr_element looks like a department header.
            try:
                if " )" in item.td.h2.text:
                    current_dept = str(item.td.h2.text.partition("(")[2].partition(" ")[0])

            # Not on a department, so use previous current_dept.
            except AttributeError:
                pass

            # The header of each class: units, department, course number, etc..
            if 'Units' in parsed_text:
                page_list.append((' NXC'))
                page_list.append(str(current_dept + " " + parsed_text.partition(' Prereq')[0]))

            # Exam Information, Section information, and Email.
            else:
                try:
                    item_class = str(item['class'][0])

                    if 'nonenrtxt' in item_class:
                        if ('FI' or 'MI') in parsed_text:
                            page_list.append(str(parsed_text))

                    elif 'sectxt' in item_class:
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

        print ("Completed Page {} of {}".format(page, number_pages))
        master.append(page_list)

    return master


def parse_list_sections(section, tracker, item, counter):
    '''Parses the section information for parse_list.'''

    number_regex = re.compile(r'\d+')
    days_regex = re.compile(r'[A-Z][^A-Z]*')

    num_loc = number_regex.search(item).start()
    to_parse = item.split(' ')

    section_num = "section " + str(counter)

    # ID.
    if num_loc == 4:
        section[section_num + " ID"] = item[4:10].strip()
        to_parse = to_parse[1:]
    else:
        section[section_num + " ID"] = 'Blank'
        to_parse[0] = to_parse[0][4:]

    # Meeting type and Section.
    section[section_num + " meeting type"] = to_parse[0]
    section[section_num + " number"] = to_parse[1]

    # Readjust the list.
    to_parse = to_parse[2:]

    # Days: so MWF would have separate entries, M, W, F. Max = 5, assumed Blank.
    if to_parse[0] != 'TBA':
        temp = days_regex.findall(to_parse[0])
        section[section_num + " day 1"] = 'Blank'
        section[section_num + " day 2"] = 'Blank'
        section[section_num + " day 3"] = 'Blank'
        section[section_num + " day 4"] = 'Blank'
        section[section_num + " day 5"] = 'Blank'

        if len(temp) == 5:
            section[section_num + " day 1"] = temp[0]
            section[section_num + " day 2"] = temp[1]
            section[section_num + " day 3"] = temp[2]
            section[section_num + " day 4"] = temp[3]
            section[section_num + " day 5"] = temp[4]
        if len(temp) == 4:
            section[section_num + " day 1"] = temp[0]
            section[section_num + " day 2"] = temp[1]
            section[section_num + " day 3"] = temp[2]
            section[section_num + " day 4"] = temp[3]
        if len(temp) == 3:
            section[section_num + " day 1"] = temp[0]
            section[section_num + " day 2"] = temp[1]
            section[section_num + " day 3"] = temp[2]
        if len(temp) == 2:
            section[section_num + " day 1"] = temp[0]
            section[section_num + " day 2"] = temp[1]
        if len(temp) == 1:
            section[section_num + " day 1"] = temp[0]
        to_parse = to_parse[1:]
    else:
        pass

    # The times.
    if to_parse[0] != 'TBA':
        timeTuples = to_parse[0].partition('-')[::2]

        section[section_num + " start time"] = timeTuples[0][:-1]
        section[section_num + " end time"] = timeTuples[1][:-1]

        section[section_num + " start time am"] = True if timeTuples[0][-1] == "a" else False
        section[section_num + " end time am"] = True if timeTuples[1][-1] == "a" else False

        to_parse = to_parse[1:]

    else:
        section[section_num + " start time"] = "TBA"
        section[section_num + " end time"] = "TBA"
        section[section_num + " start time am"] = True
        section[section_num + " end time am"] = True

    # Adjust list because time was given, but not building or room.
    if (len(to_parse) > 1) and (to_parse[0] == to_parse[1] == 'TBA'):
        to_parse = to_parse[1:]

    # The Building.
    if to_parse[0] != 'TBA':
        section[section_num + " building"] = to_parse[0]
        to_parse = to_parse[1:]
    else:
        section[section_num + " building"] = 'Blank'

    # The Room.
    section[section_num + " room"] = to_parse[0] if to_parse[0] != 'TBA' else 'Blank'

    # Readjust the list.
    to_parse = ' '.join(to_parse[1:])

    # Find position of first number in string.
    try:
        num_loc = number_regex.search(to_parse).start()
    except AttributeError:
        num_loc = 0

    # TODO
    print(to_parse)
    print(section)

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

    # TODO: Make sure to incorporate sections.
    return hash(frozenset(header.items()) | frozenset(final.items()))


def parse_list(results):
    '''Parses the list elements into their readable values to store.'''

    final = []

    for ls in results:
        # Components of a class.
        header = {}
        email = []
        final = {}
        midterm = {}
        tracker = {}
        section = collections.OrderedDict()
        counter = 0

        number_regex = re.compile(r'\d+')

        for item in ls:
            # Find class information.
            if 'Units' in item:
                # Department.
                c_department = item.partition(' ')[0]
                header["department"] = c_department
                num_loc = number_regex.search(item).start()

                # Course Number.
                c_number = item[num_loc:].partition(' ')[0]
                header["course number"] = c_number

                # Temporary variable to make lines shorter and save time.
                temp = item.partition('( ')

                # Name.
                header["course name"] = temp[0][len(c_number) + 1 + num_loc: -1]

                # Units.
                header["units"] = temp[2].partition(')')[0]

                # Restrictions.
                if num_loc != len(c_department) + 1:
                    header["restrictions"] = item[len(c_department) + 1: num_loc - 1]
                else:
                    header["restrictions"] = "No Restrictions"

            # What happens with two emails? Need to modify getData as well.

            # Find Email Info.
            if (('No Email' in item) or ('.edu' in item)) and (item.strip() not in email):
                if (not email) or ('No Email' not in item):
                    email.append(item.strip())

            # Finds Section Info.
            if '....' in item:
                counter += 1
                parse_list_sections(section, tracker, item, counter)

            # Finds Final / Midterm Info.
            if ('FI' or 'MI') in item:
                exam = item.split(' ')

                temp2 = {}

                temp2["date"] = exam[1]
                temp2["day"] = exam[2]

                # The start and end times.
                if exam[3] != 'TBA':
                    temp.extend(exam[3].partition('-')[::2])
                    timeTuples = exam[3].partition('-')[::2]

                    temp2["start time"] = timeTuples[0][:-1]
                    temp2["end time"] = timeTuples[1][:-1]

                    temp2["start time am"] = True if timeTuples[0][-1] == "a" else False
                    temp2["end time am"] = True if timeTuples[1][-1] == "a" else False

                else:
                    temp2["start time"] = "TBA"
                    temp2["end time"] = "TBA"
                    temp2["start time am"] = True
                    temp2["end time am"] = True

                if 'FI' in item:
                    final = temp2
                else:
                    midterm = temp2

        # FIXME: How to reduce function call to generate_key?
        key = generate_key(header, section, final)

        key_tracker = dict()
        key_tracker = {key: [tracker]}

        """Important: If you have a list of collision keys,
           put one in here to determine the problematic classes."""
        # if (key == -5895194357248003337):
        #     print(header, section, tracker)

        final.append([header, section, email, midterm, final, key_tracker, key])


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
        with open("dataset3.txt", "w") as open_file:
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
    """ Adds data to firebase."""

    db = firebase.FirebaseApplication("https://schedule-of-classes.firebaseio.com")

    path = "/Classes/quarter/SUMMER 2017/"

    for i in ls:
        key = i[-1]
        result = db.post(path + str(key), i[:-2])


def main():
    '''The main function.'''

    # Global Variables.
    global s
    global number_pages

    # Update postData and request session for previously parsed classes.
    quarter = update_data()

    post = s.post(SOC_URL, data=POST_DATA, stream = True)

    # Define rough boundaries where the page number should be.
    begin = int(re.search(r"Page", str(post.content)).start()) + 22

    # The total number of pages to parse and the current page starting at 1.
    number_pages = int(str(post.content)[begin:begin + 6].partition(')')[0])

    # Prints which quarter we are fetching data from and how many pages.
    print("Fetching data for {} from {} pages\n".format(quarter, number_pages))

    # Groups a url with its page number.
    pages = list(range(1, number_pages + 1))
    urls = (SOC_URL + str(x) for x in pages)
    tied = zip(urls, pages)

    # Gets the data using urls.
    results = get_data(tied)

    # Format list into proper format
    results = format_list(results)

    # Parses items in list into usable portions.
    final = parse_list(results)

    return final


if __name__ == '__main__':
    DONE = main()

    # If our unique ID keys aren't for some reason unique, we want to stop.
    if check_collision_key(DONE) is False:
        print("ERROR: Hashing algorithm encountered a collision!")
        sys.exit()

    # Writes the data to a file.
    # write_to_db(DONE)
