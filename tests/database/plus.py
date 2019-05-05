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

    return result

plus()
