from time import sleep
import sys
for i in range(10):
    if i % 2 == 0:
        print(i, file=sys.stderr)
    else:
        print(i)
    sleep(0.5)
