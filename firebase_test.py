import json
from firebase import firebase


def main():
    # authentication = firebase.Authentication("aykanfonseca5@gmail.com", extra={'id': Ah1V2SSqlWct3INN4rxdRDXIJ4G2})

    # firebase.authentication = authentication

    f = firebase.FirebaseApplication("https://scheduleofclasses-91ba3.firebaseio.com/", None)

    result = f.post('/users', {'ID' :  'CHOCOLATE'})
    print result

if __name__ == "__main__":
    main()
