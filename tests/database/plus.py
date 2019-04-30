import sys


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
    with open("data/number.dat") as file:
        n = int(file.read())
    print(n)
    result_fib = fibonacci(n)
    result_fact = factorial(n)
    result = result_fib + result_fact
    print(result_fib)
    print(result_fact)
    print(result)
    return result


plus()
