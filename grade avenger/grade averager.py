#its a pythom file, grade averager.py

x= input("How many grades do you want to enter in to the database? ")
gradecount=int(x)
total=0

for i in range(0,gradecount):
    y=input("Enter the grade you got on the assignment out of 100 ")
    y2=float(y)
    total+=y2
average=total/gradecount
print(f"Your grade average is {average}")
if average < 50:
    print("Wow you failed and you are a failure")
else:
    print("Wow you're not a failure and passed")