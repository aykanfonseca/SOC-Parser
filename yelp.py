def main():
    """For some reason, this doesn't work in Python 2. Use Python 3. Specifically the problem with Python 2
       is that it returns the rating first and then the id for each element: {'rating' : 5, 'id' : 100}."""

    ex = [{'id': 1000, 'rating': 5}, {'id': 1003, 'rating': 1}, {'id': 1002, 'rating': 4}, {'id': 1009, 'rating': 5}]

    # Needs the reverse=True parameter to preserve ordering.
    print(sorted(ex, key=lambda x: x['rating'], reverse=True))


    """Basic approach: Have five lists and each time you come across a rating with the correct value,
       append it to the end of that list (preserves the relative ordering among same rating elements).

       Then concat at end."""
    # five_ls, four_ls, three_ls, two_ls, one_ls = [], [], [], [], []
    #
    # for i in ex:
    #     if i['rating'] == 5:
    #         five_ls.append(i)
    #     elif i['rating'] == 4:
    #         four_ls.append(i)
    #     elif i['rating'] == 3:
    #         three_ls.append(i)
    #     elif i['rating'] == 2:
    #         two_ls.append(i)
    #     else:
    #         one_ls.append(i)
    #
    # print(five_ls + four_ls + three_ls + two_ls + one_ls)

if __name__ == "__main__":
    main()
