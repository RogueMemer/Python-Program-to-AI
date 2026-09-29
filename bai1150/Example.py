# this is my python program
# it does stuff. idk.

print("welcome to my program lol")

x = input("give me a number: ")

# i forgot to convert it so this might break idk
try:
    x = int(x)
except:
    print("bro thats not even a number")
    x = 0  # default because why not

# random logic that makes no sense
if x > 10:
    print("wow thats a big number")
elif x == 10:
    print("its literally 10")
else:
    print("small number detected")

# totally unnecessary loop
for i in range(3):
    print("looping for no reason:", i)

print("ok program over bye")

import pandas as pd

df = pd.DataFrame({"Name": ["Alice", "Bob"], "Age": [25, 30]})
print(df)