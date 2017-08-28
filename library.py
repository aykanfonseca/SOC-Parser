import requests
from bs4 import BeautifulSoup
from firebase import firebase

bookstore_url = "https://ucsdbkst.ucsd.edu/wrtx/TextSearch?section="

def main():
    database = firebase.FirebaseApplication("https://schedule-of-classes-8b222.firebaseio.com/", None)
    result = database.get('/quarter/FA17', None)

    term = "FA17"
    urls = []

    for key, value in result.items():
        subject = value["department"]
        course_num = value["course number"]
        url = bookstore_url + str(key) + "&term=" + term + "&subject=" + subject + "&course=" + course_num
        urls.append(url)

    print(urls[5])

    post = requests.get(urls[5])
    soup = BeautifulSoup(post.content, 'lxml').findAll('td')

    content = []

    for index, value in enumerate(soup):
        try:
            if (value["align"] == "CENTER" and value.font is not None):
                book = soup[index+2].text.partition(", ")
                content.append({"isRequired": True if soup[index].text == "R" else False, "Author": soup[index+1].text, "Book Title" : book[0], "Book ISBN" : book[2]})
        except:
            pass

    print(content)

if __name__ == '__main__':
    main()
