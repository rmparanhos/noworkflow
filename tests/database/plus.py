import mysql.connector

def plus():
    print("------db--------") #pep 249 contem as diretrizes para api de conexao a db
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="root",
        database="plus"
    )

    mycursor = mydb.cursor()

    mycursor.execute("SELECT * FROM letter")

    myresult = mycursor.fetchall()

    for x in myresult:
        print(x[0])


    mycursor.execute("SELECT * FROM number WHERE n > 4")
    myresult = mycursor.fetchall()

    for x in myresult:
        print(x[0])

    mycursor.execute("SELECT * FROM number JOIN number_letter ON number.n = number_letter.n")
    myresult = mycursor.fetchall()

    for x in myresult:
        print(x[0])

    mycursor.execute("SELECT * FROM number JOIN number_letter ON number.n = number_letter.n INNER JOIN letter on number_letter.c = letter.c")
    myresult = mycursor.fetchall()

    for x in myresult:
        print(x[0])

    mycursor.execute("SELECT * FROM number_letter WHERE n IN (SELECT n FROM number)")
    myresult = mycursor.fetchall()

    for x in myresult:
        print(x[0])

    mycursor.execute("INSERT INTO letter VALUES('R')")

    mydb.commit()
    return "Experimento encerrado com sucesso"


print(plus())
