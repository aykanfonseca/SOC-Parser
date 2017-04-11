import requests
from bs4 import BeautifulSoup

bookstore_url = "https://ucsdbkst.ucsd.edu/wrtx/TextSearch?section="

def readFile(ls):
    with open("dataset2.txt", "r") as file:
        for item in Final:
            for i in item:
                file.write(str(i))

            file.write("\n")
            file.write("\n")

def addUniqueCode(ls):
    # Assign unique code to each item.
    counter = 1
    for item in ls:
        item.insert(0, counter)
        counter += 1

def main(ls, quarter):


    addUniqueCode(ls)

    # Create a dictionary.
    done = dict()

    # Get the books.
    for item in ls:
        dept = item[1][0]
        course = item[1][1]
        section = item[2][0]
        term = quarter

        lastname = item[2][10]
        firstname = item[2][11]

        unique = dept + course + lastname + firstname

        # We haven't done this before.
        if unique not in done:
            done[unique] = item[0]
            print (unique, item[0])
            post = requests.get(bookstore_url+section+"&term="+term+"&subject="+dept+"&course="+course)
            soup = BeautifulSoup(post.content, 'lxml')
        else:
            print done[unique]

if __name__ == '__main__':
    main()
