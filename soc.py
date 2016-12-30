from bs4 import BeautifulSoup
from datetime import datetime
from time import time
import requests, itertools, re

# Starts the timer.
start = time()

# Relevant Year Data for current year (cYear) and next year (nYear) but only the last two digits.
year = datetime.now().year
cY = repr(year % 100)
nY = repr(year + 1 % 100)

# This is the URL to the entire list of classes.
URL = 'https://act.ucsd.edu/scheduleOfClasses/scheduleOfClassesStudentResult.htm?page='
URL2 = 'http://blink.ucsd.edu/instructors/courses/schedule-of-classes/subject-codes.html'

# Input data besides classes.
postData = {
    'loggedIn': 'false', 'instructorType': 'begin', 'titleType': 'contain',
    'schDay': ['M', 'T', 'W', 'R', 'F', 'S'], 'schedOption1': 'true',
    'schedOption2': 'true', 'schStartTime': '12:00', 'schStartAmPm': '0',
    'schEndTime': '12:00', 'schEndAmPm': '0', 'tabNum': 'tabs-sub',
    'schedOption1Dept': 'true', 'schedOption2Dept': 'true',
    'schDayDept': ['M', 'T', 'W', 'R', 'F', 'S'], 'schStartTimeDept': '12:00',
    'schStartAmPmDept': '0', 'schEndTimeDept': '12:00', 'schEndAmPmDept': '0'}

# Gets all the quarters listed in drop down menu.
def getQuarters(URL, current=None):
    quarters = requests.post(URL)
    qSoup = BeautifulSoup(quarters.content, 'lxml')

    # Current quarter by optional parameter.
    if current:
        for option in qSoup.findAll('option'):
            value = option['value']
            if value[2:] in (cY, nY):
                return value

    # Gets the rest of the quarters for the year.
    else:
        quarters = []
        for option in qSoup.findAll('option'):
            # Value will take the form 'FA16' or 'SP15' for example.
            value = option['value']
            if value[2:] in (cY, nY):
                quarters.append(value)

        return quarters

# Gets all the subjects listed in select menu.
def getSubjects():
    # Makes the post request for the Subject Codes.
    subjectPost = requests.post(URL2)
    subjectSoup = BeautifulSoup(subjectPost.content, 'lxml')

    # Gets all the subject Codes for post request.
    subjects = {}
    for x in subjectSoup.findAll('td'):
        if len(x.text) <= 4:
            subjects.setdefault('selectedSubjects', []).append(str(x.text))

    return subjects

# Updates term and post request using the current quarter by calling get_current_quarter.
def updateTerm():
    term = {'selectedTerm': getQuarters(URL, current='yes')}
    postData.update(term)

# Updates the post request and subjects selected by parsing URL2.
def updateSubjects():
    # postData.update(getSubjects())
    postData.update({'selectedSubjects' : 'CSE'})

# Calls updateSubjects & updateTerm to add to post data.
def updatePost():
    updateTerm()
    updateSubjects()

# Parses the data of one page.
def getData(url):
    # Occasionally, the first call will fail.
    try:
        post = s.get(url)
    except:
        post = s.get(url)

    soup = BeautifulSoup(post.content, 'lxml')
    tr_elements = soup.findAll('tr')
    span_elements = soup.findAll('span', {'class': 'centeralign'})

    # Gets the list of departments in the current page.
    departments = [str(x.text.partition("(")[2].partition(" ")[0]) for x in span_elements if ' )' in x.text]

    counter = 0
    SOC = []

    # Used to switch departments.
    for item in tr_elements:
        parsedText = str(' '.join(item.text.split()))

        # Next one if you find selected text b/c new subject is shown.
        if all(x in parsedText for x in ['Course Number', 'ID']):
            # currentDept = next(departments)
            currentDept = departments[counter]
            counter += 1

        # The header of each class: units, department, course number, etc..
        if ('Units' in parsedText):
            SOC.append(' NXC')
            SOC.append((currentDept + ' ' + parsedText).partition(' Prereq')[0])

        # Final / Midterm Information, Section information (Discussion and Labs), and Email.
        else:
            try:
                itemClass = str(item['class'][0])
            except KeyError:
                itemClass = ''

            if (itemClass == 'nonenrtxt'):
                if (('FI' or 'MI') in parsedText):
                    SOC.append(parsedText)

            if (itemClass == 'sectxt'):
                if 'Cancelled' not in parsedText:
                    SOC.append('....' + parsedText)

                    try:
                        email = str(item.find('a')['href'])[7:]
                    except TypeError:
                        email = 'No Email'

                    SOC.append(email)

    print ("Completed Page {} of {}").format(url.partition('=')[2].partition(' ')[0], numberPages)
    return SOC

# Parses the list elements into their readable values to store.
def parseList(ls):
    # Components of a class.
    Header, Email, Final, Midterm, Section = [], [], [], [], []

    for item in ls:
        # Find class information.
        if 'Units' in item:
            # Department.
            C_department = item.partition(' ')[0].strip()
            Header.append(C_department)
            num_loc = re.search(r'\d+', item).start()

            # Course Number.
            C_number = item[num_loc:].partition(' ')[0].strip()
            Header.append(C_number)

            # Name.
            Header.append(item.partition('( ')[0][len(C_number) + 1 + num_loc:].strip())

            # Units.
            Header.append(item.partition('( ')[2].partition('s)')[0]+'s')

            # Restrictions.
            if num_loc != len(C_department) + 1:
                Header.append(item[len(C_department) + 1:num_loc].strip())
            else:
                Header.append('No Restrictions')
        pass

        # TODO : What happens if there are two emails? Need to modify getData as well.

        # Find Email Info.
        if (('No Email' in item) or ('.edu' in item)) and (item.strip() not in Email):
            if (len(Email) == 0) or ('No Email' not in item):
                Email.append(item.strip())
        pass

        # Finds Section Info.
        if ('....' in item):
            num_loc = re.search(r'\d+', item).start()
            S = item.split(' ')

            # ID.
            if (num_loc == 4):
                Section.append(item[4:10].strip())
                S = S[1:]
            else:
                Section.append('Blank')
                S[0] = S[0][4:]

            # Meeting type and Section.
            Section.extend(S[0:2])

            # Readjust the list.
            S = S[2:]

            # Days: so MWF would have separate entries, M, W, F.
            if S[0] != 'TBA':
                temp = re.findall('[A-Z][^A-Z]*', S[0])
                # Day 1, Day 2, and Day 3.
                if len(temp) == 3:
                    Section.extend(temp)
                if len(temp) == 2:
                    Section.extend(temp)
                    Section.append('Blank')
                if len(temp) == 1:
                    Section.append(temp[0])
                    Section.append('Blank')
                    Section.append('Blank')
                S = S[1:]
            else:
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')

            # The times.
            if S[0] != 'TBA':
                Section.extend(S[0].partition('-')[::2])
                S = S[1:]
            else:
                Section.append('Blank')
                Section.append('Blank')

            # Adjust list in the case that the time was given, but not the building or room.
            if (len(S) > 1) and (S[0] == S[1] == 'TBA'):
                S = S[1:]

            # The Building.
            if S[0] != 'TBA':
                Section.append(S[0])
                S = S[1:]
            else:
                Section.append('Blank')

            # The Room.
            if S[0] != 'TBA':
                Section.append(S[0])
            else:
                Section.append('Blank')

            # Readjust the list.
            S = ' '.join(S[1:])

            # Find position of first number in string.
            try:
                num_loc = re.search(r'\d+', S).start()
            except AttributeError:
                num_loc = 0

            # Handles Teacher, Seats Taken, and Seats Offered.
            if 'FULL' in S:
                temp = S.find('FULL')
                if (temp == 0):
                    Section.append('Blank')
                    Section.append('Blank')
                    Section.append('Blank')
                else:
                    if 'Staff' in S:
                        Section.append('Staff')
                        Section.append('Blank')
                        Section.append('Blank')
                    else:
                        name = S[:temp].strip()

                        # First name.
                        Section.append(name.partition(',')[0])
                        # Last name.
                        Section.append(name.partition(',')[2].strip().split(' ')[0])

                        # Middle name.
                        try:
                            Section.append(name.partition(',')[2].strip().split(' ')[1])
                        except:
                            Section.append('Blank')

                # Adjust String.
                S = S[temp:]

                # Seats Taken.
                Section.append(S[:(S.find(')')+1)])

                # Seats Available.
                Section.append(S[(S.find(')')+2):])

            elif 'Unlim' in S:
                if 'Staff ' in S:
                    # First, Last, middle names.
                    Section.append('Staff')
                    Section.append('Blank')
                    Section.append('Blank')
                    # Seat Information.
                    Section.append('Unlim')
                    Section.append('Unlim')
                else:
                    name = S[:S.find('Unlim')-1]

                    # First name.
                    Section.append(name.partition(',')[0])
                    # Last name.
                    Section.append(name.partition(',')[2].strip().split(' ')[0])

                    # Middle name.
                    try:
                        Section.append(name.partition(',')[2].strip().split(' ')[1])
                    except:
                        Section.append('Blank')

                    # Seat information.
                    Section.append('Unlim')
                    Section.append('Unlim')

            # Name and seat information.
            elif num_loc != 0:
                name = S[:num_loc].strip()

                # First name.
                if (name.partition(',')[0] != ''):
                    Section.append(name.partition(',')[0])
                else:
                    Section.append('Blank')

                # Last name.
                if (name.partition(',')[2].strip().split(' ')[0] != ''):
                    Section.append(name.partition(',')[2].strip().split(' ')[0])
                else:
                    Section.append('Blank')

                # Middle name.
                try:
                    Section.append(name.partition(',')[2].strip().split(' ')[1])
                except:
                    Section.append('Blank')

                temp = S[num_loc:].strip().split(' ')
                Section.append(temp[0])
                Section.append(temp[1])

            # Just staff and no seat information.
            elif S.strip() == 'Staff':
                Section.append('Staff')
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')

            # Name and no seat information.
            elif num_loc == 0:
                name = S.strip()

                # First name.
                if (name.partition(',')[0] != ''):
                    Section.append(name.partition(',')[0])
                else:
                    Section.append('Blank')

                # Last name.
                if (name.partition(',')[2].strip().split(' ')[0] != ''):
                    Section.append(name.partition(',')[2].strip().split(' ')[0])
                else:
                    Section.append('Blank')

                # Middle name.
                try:
                    Section.append(name.partition(',')[2].strip().split(' ')[1])
                except:
                    Section.append('Blank')

                # Blanks for both the seat information.
                Section.append('Blank')
                Section.append('Blank')

            # No name and no seat information
            else:
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')
        pass

        # Finds Final Info.
        if 'FI' in item:
            F = item.split(' ')

            # Date and Day.
            Final.extend(F[1:3])

            # The start and end times.
            if F[3] != 'TBA':
                Final.extend(F[3].partition('-')[::2])
            else:
                Final.append('TBA')
                Final.append('TBA')

            # Building and Room.
            Final.extend(F[4:])
        pass

        # Finds Midterm Info.
        if 'MI' in item:
            M = item.split(' ')

            # Date and Day.
            Midterm.extend(M[1:3])

            # The start and end times.
            if M[3] != 'TBA':
                Midterm.extend(M[3].partition('-')[::2])
            else:
                Midterm.append('TBA')
                Midterm.append('TBA')

            # Building and Room.
            Midterm.extend(M[4:])
        pass

    return [Header, Section, Email, Midterm, Final]

# Formats the result list into the one we want
def formatList(ls):
    # # Flattens list of lists into list.
    parsedSOC = [item for sublist in ls for item in sublist]

    # Spliting a list into lists of lists based on a delimiter word.
    parsedSOC = [list(y) for x, y in itertools.groupby(parsedSOC, lambda z: z == ' NXC') if not x]
    # parsedSOC = [list(y) for x, y in itertools.groupby(ls, lambda z: z == ' NXC') if not x]

    # Sorts list based on sorting criteria.
    return [x for x in parsedSOC if len(x) > 2 and not 'Cancelled' in x]

# Gets the data for Cape scrape: format like this, 'CSE 100 Alvarado Christine J.'.
def uniqueValues(ls):
    local = [' '.join([item[0][0], item[0][1]+ ":", item[1][10] + ",", item[1][11], item[1][12]]) for item in ls]

    found = set()
    for item in local:
        if item not in found:
            found.add(item)

    return list(found)

# The main function.
def main():
    global s, numberPages

    # Update postData and request session for previously parsed classes.
    updatePost()

    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0'
    post = s.post(URL, data=postData)
    soup = BeautifulSoup(post.content, 'lxml')

    # The total number of pages to parse and the current page starting at 1.
    numberPages = int(soup.text[re.search(r"Page", soup.text).start()+12:].partition(')')[0])

    urls = [URL + str(x) for x in xrange(1, numberPages + 1)]

    # Gets the data using urls.
    results = [getData(i) for i in urls]

    # Format list into proper format
    results = formatList(results)

    # Parses items in list into usable portions.
    final = [parseList(item) for item in results]

    for item in final:
        print item
        print '\n'

    return final

# The main algorithm that employes functions to get the data.
if __name__ == '__main__':
    main()

    # Ends the timer.
    end = time()

    # Prints how long it took for program to run.
    print('\n' + str(end - start) )
