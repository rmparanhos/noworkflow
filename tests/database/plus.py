import sys
import mysql.connector

def factorial(n):
    fat = 1
    i = 2
    while i <= n:
        fat = fat * i
        i = i + 1
    return fat


def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def plus():
    print('sera_interrogacao')
    with open("data/number.dat") as file:
        n = int(file.read())
    print(n)
    result_fib = fibonacci(n)
    result_fact = factorial(n)
    result = result_fib + result_fact
    print(result_fib)
    print(result_fact)
    print(result)
    with open("data/result.dat", "a") as file:
        file.write(result.__str__())
    print("------db--------") #pep 249 contem as diretrizes para api de conexao a db
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="root",
        database="plus"
    )

    mycursor = mydb.cursor()

    mycursor.execute("SELECT * FROM number")

    myresult = mycursor.fetchall()

    for x in myresult:
        print(x[0])

    mycursor.execute("SELECT * FROM letter")

    myresult = mycursor.fetchall()

    for x in myresult:
        print(x[0])

    return result


plus()

# output:
r'''
C:\Users\raffa\Desktop\Trabalhos 10 Periodo\E-Science\Trabalho noWorkflow\noworkflow\tests\database>now show 3 -f
teste
[now] trial information:
  Id: 3
  Inherited Id: None
  Script: plus.py
  Code hash: e541a9dfa93c43e815c5c1a934869737c54f650f
  Start: 2019-05-08 01:08:26.453506
  Finish: 2019-05-08 01:08:55.202960
  Duration: 0:00:28.749454
[now] this trial accessed the following files:
  Name: nul
    Mode: w
    Buffering: default
    Content hash before: None
    Content hash after: None
    Timestamp: 2019-05-08 01:08:48.821711
    Function:  ... -> open

  Name: data/number.dat
    Mode: r
    Buffering: default
    Content hash before: 77de68daecd823babbb58edb1c8e14d7106e83bb
    Content hash after: 77de68daecd823babbb58edb1c8e14d7106e83bb
    Timestamp: 2019-05-08 01:08:53.965653
    Function: plus -> open

  Name: data/result.dat
    Mode: a
    Buffering: default
    Content hash before: 39a429d03cd86c88b6e5e52205add5502226715e
    Content hash after: 39a429d03cd86c88b6e5e52205add5502226715e
    Timestamp: 2019-05-08 01:08:53.979646
    Function: plus -> open
[now] this trial accessed the following database:
  Name: plus
    Host: localhost
    User: root
    DML: [('number', 'SELECT * FROM number', '972a67c48192728a34979d9a35164c1295401b71'), ('letter', 'SELECT * FROM letter', '86f7e437faa5a7fce15d1ddcb9eaeaea377667b8')]
    Mode: r
    Buffering: default
    Content hash before: None
    Content hash after: None
    Timestamp: 2019-05-08 01:08:53.985641
    Function: plus -> connect ->  ... -> open
'''